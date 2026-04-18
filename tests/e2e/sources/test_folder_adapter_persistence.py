"""E2E — FolderSourceAdapter → IntakePackageSink → real PostgreSQL (Phase 1d G0.3).

@test_registry
suite: phase_1d_e2e
component: sources.folder_adapter, sources.sink, state.repositories.intake
covers:
    - src/aiflow/sources/folder_adapter.py
    - src/aiflow/sources/sink.py
    - src/aiflow/intake/association.py
    - src/aiflow/sources/observability.py
phase: 1d
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1d, intake, source_adapter, folder, sink, postgres]

Validates the G0.3 deliverable for ``FolderSourceAdapter``: a file is
dropped into the watched directory, the watchdog handler is bypassed in
favour of the deterministic ``_note_event`` injection (the underlying
drain pipeline is identical — see the unit-test pattern in
``tests/unit/sources/test_folder_adapter.py``), and the surfaced package
is threaded through :func:`process_next` into an :class:`IntakePackageSink`
bound to real Docker PostgreSQL (port 5433). The adapter does NOT ingest
descriptions, so ``association_mode`` stays NULL and the 037 CHECK trigger
is not exercised.

NOTE (feedback_asyncpg_pool_event_loop.md): all DB-touching assertions live
in one ``@pytest.mark.asyncio`` method to share a single event-loop-bound
pool across them. The watchdog Observer is intentionally NOT started
(``auto_start=False``) so the test is independent of OS-level FS-event
timing — see the kickoff prompt's STOP feltetel for race avoidance.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from structlog.testing import capture_logs

from aiflow.api.deps import get_pool
from aiflow.sources import FolderSourceAdapter, IntakePackageSink, process_next
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


async def test_folder_adapter_persists_through_sink_to_postgres(tmp_path: Path) -> None:
    tenant_id = f"tenant-G0.3-folder-{uuid4().hex[:8]}"
    watch_root = tmp_path / "watch"
    watch_root.mkdir()
    storage_root = tmp_path / "folder_storage"

    payload = b"%PDF-1.4\nG0.3 folder fixture\n"
    src_path = watch_root / "report.pdf"
    src_path.write_bytes(payload)

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    adapter._note_event(src_path)

    pool = await get_pool()
    repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=repo)

    try:
        with capture_logs() as events:
            processed = await process_next(adapter, sink)
            assert processed is True

            # Adapter is idle once the only ripe file has drained.
            processed_again = await process_next(adapter, sink)
            assert processed_again is False

        # --- Canonical observability assertions ----------------------------
        persisted = [e for e in events if e.get("event") == "source.package_persisted"]
        assert len(persisted) == 1, f"expected 1 persisted event, got {len(persisted)}: {events}"
        rec = persisted[0]
        assert rec["source_type"] == "folder"
        assert rec["tenant_id"] == tenant_id
        assert rec["file_count"] == 1
        assert rec["description_count"] == 0
        # FolderSourceAdapter does not ingest descriptions, so the associator
        # short-circuits and association_mode stays NULL.
        assert rec["association_mode"] is None

        received = [e for e in events if e.get("event") == "source.package_received"]
        assert len(received) == 1
        assert received[0]["source_type"] == "folder"

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
            assert pkg_row["source_type"] == "folder_import"
            assert pkg_row["tenant_id"] == tenant_id
            # No descriptions → association_mode is NULL by design (037
            # CHECK trigger only fires when descriptions exist).
            assert pkg_row["association_mode"] is None

            file_rows = await conn.fetch(
                "SELECT file_id, file_name, size_bytes FROM intake_files WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(file_rows) == 1
            assert file_rows[0]["file_name"] == "report.pdf"
            assert file_rows[0]["size_bytes"] == len(payload)

            desc_count = await conn.fetchval(
                "SELECT COUNT(*) FROM intake_descriptions WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert desc_count == 0

            assoc_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM package_associations pa
                JOIN intake_files f ON f.file_id = pa.file_id
                WHERE f.package_id = $1
                """,
                pkg_row["package_id"],
            )
            assert assoc_count == 0
    finally:
        await _cleanup_tenant(pool, tenant_id)
