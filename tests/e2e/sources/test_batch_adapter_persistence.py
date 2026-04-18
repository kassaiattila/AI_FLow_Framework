"""E2E — BatchSourceAdapter → IntakePackageSink → real PostgreSQL (Phase 1d G0.4).

@test_registry
suite: phase_1d_e2e
component: sources.batch_adapter, sources.sink, state.repositories.intake
covers:
    - src/aiflow/sources/batch_adapter.py
    - src/aiflow/sources/sink.py
    - src/aiflow/intake/association.py
    - src/aiflow/sources/observability.py
phase: 1d
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1d, intake, source_adapter, batch, sink, postgres]

Validates the G0.4 deliverable for ``BatchSourceAdapter``: an in-memory ZIP
with 2 files + 2 descriptions is enqueued with an explicit
``association_mode=ORDER``. The adapter pre-associates inside ``enqueue()``
and persists the mode on the package, so when ``IntakePackageSink.handle``
runs the ``association_mode is None`` guard short-circuits and the sink
does NOT re-run ``resolve_mode_and_associations``. The persisted event and
the DB row both reflect the adapter's pre-set mode — proving the
"mode already set" branch of the sink works end-to-end.

NOTE (feedback_asyncpg_pool_event_loop.md): all DB-touching assertions live
in one ``@pytest.mark.asyncio`` method to share a single event-loop-bound
pool across them. The conftest.py autouse fixture resets ``_deps._pool``
between tests in this directory.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from structlog.testing import capture_logs

from aiflow.api.deps import get_pool
from aiflow.intake.package import (
    AssociationMode,
    DescriptionRole,
    IntakeDescription,
)
from aiflow.sources import BatchSourceAdapter, IntakePackageSink, process_next
from aiflow.state.repositories.intake import IntakeRepository

pytestmark = pytest.mark.asyncio


def _build_zip(entries: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()


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


async def test_batch_adapter_persists_through_sink_to_postgres(tmp_path: Path) -> None:
    tenant_id = f"tenant-G0.4-batch-{uuid4().hex[:8]}"
    storage_root = tmp_path / "batch_storage"

    payload_a = b"%PDF-1.4\nG0.4 batch fixture A\n"
    payload_b = b"%PDF-1.4\nG0.4 batch fixture B\n"
    archive_bytes = _build_zip([("invoice_a.pdf", payload_a), ("invoice_b.pdf", payload_b)])

    descriptions = [
        IntakeDescription(text="invoice A note", role=DescriptionRole.USER_NOTE),
        IntakeDescription(text="invoice B note", role=DescriptionRole.USER_NOTE),
    ]

    adapter = BatchSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
    )
    enqueued = adapter.enqueue(
        raw_bytes=archive_bytes,
        filename="invoices.zip",
        descriptions=descriptions,
        association_mode=AssociationMode.ORDER,
    )
    assert len(enqueued) == 1, "descriptions-bearing batch must produce a single merged package"
    pkg = enqueued[0]
    assert pkg.association_mode == AssociationMode.ORDER, (
        "BatchSourceAdapter must pre-set association_mode before sink touches it"
    )

    pool = await get_pool()
    repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=repo)

    try:
        with capture_logs() as events:
            processed = await process_next(adapter, sink)
            assert processed is True

            processed_again = await process_next(adapter, sink)
            assert processed_again is False

        # --- Canonical observability assertions ----------------------------
        persisted = [e for e in events if e.get("event") == "source.package_persisted"]
        assert len(persisted) == 1, f"expected 1 persisted event, got {len(persisted)}: {events}"
        rec = persisted[0]
        assert rec["source_type"] == "batch"
        assert rec["tenant_id"] == tenant_id
        assert rec["file_count"] == 2
        assert rec["description_count"] == 2
        # CRITICAL: sink MUST preserve the adapter's pre-set ORDER mode (not
        # overwrite via auto-inference). This proves the
        # `if package.association_mode is None` guard in IntakePackageSink.handle.
        assert rec["association_mode"] == "order"

        received = [e for e in events if e.get("event") == "source.package_received"]
        assert len(received) == 1
        assert received[0]["source_type"] == "batch"

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
            assert pkg_row["package_id"] == pkg.package_id
            assert pkg_row["source_type"] == "batch_import"
            assert pkg_row["association_mode"] == "order"

            file_rows = await conn.fetch(
                """
                SELECT file_id, file_name, size_bytes
                FROM intake_files
                WHERE package_id = $1
                ORDER BY sequence_index
                """,
                pkg_row["package_id"],
            )
            assert len(file_rows) == 2
            file_names = {r["file_name"] for r in file_rows}
            assert file_names == {"invoice_a.pdf", "invoice_b.pdf"}

            desc_rows = await conn.fetch(
                "SELECT description_id, role FROM intake_descriptions WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(desc_rows) == 2
            assert all(r["role"] == "user_note" for r in desc_rows)

            # ORDER mode: 2 files paired with 2 descriptions positionally.
            assoc_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM package_associations pa
                JOIN intake_files f ON f.file_id = pa.file_id
                WHERE f.package_id = $1
                """,
                pkg_row["package_id"],
            )
            assert assoc_count == 2
    finally:
        await _cleanup_tenant(pool, tenant_id)
