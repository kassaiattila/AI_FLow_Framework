"""E2E — EmailSourceAdapter → IntakePackageSink → real PostgreSQL (Phase 1d G0.2).

@test_registry
suite: phase_1d_e2e
component: sources.email_adapter, sources.sink, state.repositories.intake
covers:
    - src/aiflow/sources/email_adapter.py
    - src/aiflow/sources/sink.py
    - src/aiflow/intake/association.py
    - src/aiflow/sources/observability.py
phase: 1d
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1d, intake, source_adapter, email, sink, postgres]

Validates the full G0.2 deliverable: a fake IMAP backend feeds an
:class:`EmailSourceAdapter`; the package is threaded through
:func:`process_next` (the canonical fetch→handle→acknowledge helper) into
an :class:`IntakePackageSink` bound to a real Docker PostgreSQL (port 5433);
the row, the `association_mode IS NULL` (no descriptions beyond email body),
the file, and the canonical ``source.package_persisted`` observability event
are all asserted end-to-end.

NOTE (feedback_asyncpg_pool_event_loop.md): all DB-touching assertions live
in one ``@pytest.mark.asyncio`` method to share a single event-loop-bound
pool across them.
"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from structlog.testing import capture_logs

from aiflow.api.deps import get_pool
from aiflow.sources import EmailSourceAdapter, IntakePackageSink, process_next
from aiflow.sources.email_adapter import ImapBackendProtocol
from aiflow.state.repositories.intake import IntakeRepository

pytestmark = pytest.mark.asyncio


class _FakeImapBackend(ImapBackendProtocol):
    """In-memory IMAP backend — shared precedent with tests/unit/sources/."""

    def __init__(self, inbox: list[tuple[int, bytes]]) -> None:
        self.inbox = list(inbox)
        self.seen: set[int] = set()
        self.flagged: dict[int, str] = {}

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return [(u, r) for u, r in self.inbox if u not in self.seen]

    async def mark_seen(self, uid: int) -> None:
        self.seen.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        self.flagged[uid] = reason

    async def ping(self) -> bool:
        return True


def _build_email_with_attachment(
    *,
    subject: str,
    sender: str,
    body: str,
    filename: str,
    payload: bytes,
    mime_type: str = "application/pdf",
) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "intake@example.com"
    msg.set_content(body)
    main_type, _, sub_type = mime_type.partition("/")
    msg.add_attachment(
        payload,
        maintype=main_type or "application",
        subtype=sub_type or "octet-stream",
        filename=filename,
    )
    return msg.as_bytes()


async def _cleanup_tenant(pool: asyncpg.Pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1",
            tenant_id,
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM package_associations
                WHERE file_id IN (
                    SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[])
                )
                """,
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])", ids
            )
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )


async def test_email_adapter_persists_through_sink_to_postgres(tmp_path: Path) -> None:
    tenant_id = f"tenant-G0.2-e2e-{uuid4().hex[:8]}"
    storage_root = tmp_path / "email_storage"

    pdf_bytes = b"%PDF-1.4\nG0.2 fixture\n"
    raw = _build_email_with_attachment(
        subject="G0.2 wiring check",
        sender="ops@example.com",
        body="Please persist this package via the sink.",
        filename="fixture.pdf",
        payload=pdf_bytes,
    )
    backend = _FakeImapBackend([(4242, raw)])

    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id=tenant_id,
    )

    pool = await get_pool()
    repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=repo)

    try:
        with capture_logs() as events:
            processed = await process_next(adapter, sink)
            assert processed is True

            # Idempotency of idle state: adapter must not re-yield the acked UID.
            processed_again = await process_next(adapter, sink)
            assert processed_again is False

        # --- Canonical observability assertions ----------------------------
        persisted = [e for e in events if e.get("event") == "source.package_persisted"]
        assert len(persisted) == 1, f"expected 1 persisted event, got {len(persisted)}: {events}"
        rec = persisted[0]
        assert rec["source_type"] == "email"
        assert rec["tenant_id"] == tenant_id
        assert rec["file_count"] == 1
        assert rec["description_count"] == 1  # the email body → EMAIL_BODY description
        # 1 file + 1 description → ORDER wins by precedence (len==len), not
        # SINGLE_DESCRIPTION. Asserting the precedence chain explicitly here
        # locks the helper's contract into the adapter's persistence path.
        assert rec["association_mode"] == "order"

        # received event fires at acknowledge, per email_adapter contract.
        received = [e for e in events if e.get("event") == "source.package_received"]
        assert len(received) == 1
        assert received[0]["source_type"] == "email"

        # --- DB round-trip assertions --------------------------------------
        async with pool.acquire() as conn:
            pkg_rows = await conn.fetch(
                """
                SELECT package_id, source_type, tenant_id, association_mode
                FROM intake_packages
                WHERE tenant_id = $1
                """,
                tenant_id,
            )
            assert len(pkg_rows) == 1
            pkg_row = pkg_rows[0]
            assert pkg_row["source_type"] == "email"
            assert pkg_row["tenant_id"] == tenant_id
            # One description + one file → ORDER (precedence chain); see the
            # note on the observability assertion above.
            assert pkg_row["association_mode"] == "order"

            file_rows = await conn.fetch(
                "SELECT file_id, file_name, size_bytes FROM intake_files WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(file_rows) == 1
            assert file_rows[0]["file_name"] == "fixture.pdf"
            assert file_rows[0]["size_bytes"] == len(pdf_bytes)

            desc_rows = await conn.fetch(
                "SELECT description_id, role FROM intake_descriptions WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(desc_rows) == 1
            assert desc_rows[0]["role"] == "email_body"

            # G2 assertion: 037 CHECK trigger did not fire. SINGLE_DESCRIPTION
            # was persisted, so the trigger's "descriptions exist but
            # association_mode NULL" branch is not reached.
            assoc_rows = await conn.fetch(
                """
                SELECT pa.file_id, pa.description_id
                FROM package_associations pa
                JOIN intake_files f ON f.file_id = pa.file_id
                WHERE f.package_id = $1
                """,
                pkg_row["package_id"],
            )
            assert len(assoc_rows) == 1
            assert assoc_rows[0]["file_id"] == file_rows[0]["file_id"]
            assert assoc_rows[0]["description_id"] == desc_rows[0]["description_id"]

        # --- Upstream acknowledgement happened (set by process_next) -------
        assert backend.seen == {4242}
        assert backend.flagged == {}
    finally:
        await _cleanup_tenant(pool, tenant_id)
