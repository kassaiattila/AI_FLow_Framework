"""E2E — FileSourceAdapter → IntakePackageSink → real PostgreSQL (Phase 1d G0.3).

@test_registry
suite: phase_1d_e2e
component: sources.file_adapter, sources.sink, state.repositories.intake
covers:
    - src/aiflow/sources/file_adapter.py
    - src/aiflow/sources/sink.py
    - src/aiflow/intake/association.py
    - src/aiflow/sources/observability.py
phase: 1d
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1d, intake, source_adapter, file, sink, postgres]

Validates the G0.3 deliverable for ``FileSourceAdapter``: a push-mode upload
is enqueued through ``FileSourceAdapter.enqueue()``, the queued package is
threaded through :func:`process_next` (canonical fetch→handle→acknowledge)
into an :class:`IntakePackageSink` bound to real Docker PostgreSQL (port
5433); the row, the canonical ``association_mode`` (``order`` for the
1-file/1-description fixture per associator precedence), the file, the
description, the package_association row, and the
``source.package_persisted`` event are all asserted end-to-end.

NOTE (feedback_asyncpg_pool_event_loop.md): all DB-touching assertions live
in one ``@pytest.mark.asyncio`` method to share a single event-loop-bound
pool across them.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from structlog.testing import capture_logs

from aiflow.api.deps import get_pool
from aiflow.sources import FileSourceAdapter, IntakePackageSink, process_next
from aiflow.state.repositories.intake import IntakeRepository

pytestmark = pytest.mark.asyncio


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


async def test_file_adapter_persists_through_sink_to_postgres(tmp_path: Path) -> None:
    tenant_id = f"tenant-G0.3-file-{uuid4().hex[:8]}"
    storage_root = tmp_path / "file_storage"

    pdf_bytes = b"%PDF-1.4\nG0.3 file fixture\n"
    adapter = FileSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
    )
    enqueued = adapter.enqueue(
        raw_bytes=pdf_bytes,
        filename="invoice.pdf",
        description="Please process this invoice.",
    )

    pool = await get_pool()
    repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=repo)

    try:
        with capture_logs() as events:
            processed = await process_next(adapter, sink)
            assert processed is True

            # Idle after the only queued package drains.
            processed_again = await process_next(adapter, sink)
            assert processed_again is False

        # --- Canonical observability assertions ----------------------------
        persisted = [e for e in events if e.get("event") == "source.package_persisted"]
        assert len(persisted) == 1, f"expected 1 persisted event, got {len(persisted)}: {events}"
        rec = persisted[0]
        assert rec["source_type"] == "file"
        assert rec["tenant_id"] == tenant_id
        assert rec["file_count"] == 1
        assert rec["description_count"] == 1
        # 1 file + 1 description → ORDER wins by precedence (len==len), not
        # SINGLE_DESCRIPTION. Mirrors the email-adapter G0.2 assertion.
        assert rec["association_mode"] == "order"

        received = [e for e in events if e.get("event") == "source.package_received"]
        assert len(received) == 1
        assert received[0]["source_type"] == "file"

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
            assert pkg_row["package_id"] == enqueued.package_id
            assert pkg_row["source_type"] == "file_upload"
            assert pkg_row["tenant_id"] == tenant_id
            assert pkg_row["association_mode"] == "order"

            file_rows = await conn.fetch(
                "SELECT file_id, file_name, size_bytes FROM intake_files WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(file_rows) == 1
            assert file_rows[0]["file_name"] == "invoice.pdf"
            assert file_rows[0]["size_bytes"] == len(pdf_bytes)

            desc_rows = await conn.fetch(
                "SELECT description_id, role FROM intake_descriptions WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(desc_rows) == 1
            assert desc_rows[0]["role"] == "user_note"

            # G2 assertion: 037 CHECK trigger did not fire — descriptions
            # exist AND association_mode is set ('order'), so the trigger's
            # NULL-mode-with-descriptions branch is not reached.
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
    finally:
        await _cleanup_tenant(pool, tenant_id)
