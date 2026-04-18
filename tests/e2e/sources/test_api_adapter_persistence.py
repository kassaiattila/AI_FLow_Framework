"""E2E — ApiSourceAdapter → IntakePackageSink → real PostgreSQL (Phase 1d G0.4).

@test_registry
suite: phase_1d_e2e
component: sources.api_adapter, sources.sink, state.repositories.intake
covers:
    - src/aiflow/sources/api_adapter.py
    - src/aiflow/sources/sink.py
    - src/aiflow/intake/association.py
    - src/aiflow/sources/observability.py
phase: 1d
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1d, intake, source_adapter, api, sink, postgres]

Validates the G0.4 deliverable for ``ApiSourceAdapter`` (Path A — wired
through the sink in test code only; the production webhook router
``POST /api/v1/sources/webhook`` is queued for a separate session and
will use ``IntakePackageSink`` when it lands). The test constructs a
valid HMAC-SHA256 signature in-line, drives ``enqueue()`` directly, and
threads through :func:`process_next` into a sink bound to real Docker
PostgreSQL (port 5433). The adapter does NOT ingest descriptions, so
``association_mode`` stays NULL and the 037 CHECK trigger is not exercised.

NOTE (feedback_asyncpg_pool_event_loop.md): all DB-touching assertions live
in one ``@pytest.mark.asyncio`` method to share a single event-loop-bound
pool across them. The conftest.py autouse fixture resets ``_deps._pool``
between tests in this directory.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from structlog.testing import capture_logs

from aiflow.api.deps import get_pool
from aiflow.sources import ApiSourceAdapter, IntakePackageSink, process_next
from aiflow.state.repositories.intake import IntakeRepository

pytestmark = pytest.mark.asyncio


def _sign(secret: bytes, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


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


async def test_api_adapter_persists_through_sink_to_postgres(tmp_path: Path) -> None:
    tenant_id = f"tenant-G0.4-api-{uuid4().hex[:8]}"
    storage_root = tmp_path / "api_storage"
    secret = b"G0.4-test-shared-secret"

    payload = b"%PDF-1.4\nG0.4 api fixture\n"
    filename = "webhook_invoice.pdf"
    fixed_now = 1_700_000_000
    timestamp = str(fixed_now)
    signature = _sign(secret, timestamp, payload)

    adapter = ApiSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        hmac_secret=secret,
        now=lambda: fixed_now,
    )
    enqueued = adapter.enqueue(
        payload=payload,
        filename=filename,
        signature=signature,
        timestamp=timestamp,
        idempotency_key="G0.4-test-key-001",
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
        assert rec["source_type"] == "api"
        assert rec["tenant_id"] == tenant_id
        assert rec["file_count"] == 1
        assert rec["description_count"] == 0
        # ApiSourceAdapter does not ingest descriptions, so the associator
        # short-circuits and association_mode stays NULL.
        assert rec["association_mode"] is None

        received = [e for e in events if e.get("event") == "source.package_received"]
        assert len(received) == 1
        assert received[0]["source_type"] == "api"

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
            assert pkg_row["source_type"] == "api_push"
            assert pkg_row["association_mode"] is None

            file_rows = await conn.fetch(
                "SELECT file_id, file_name, size_bytes FROM intake_files WHERE package_id = $1",
                pkg_row["package_id"],
            )
            assert len(file_rows) == 1
            assert file_rows[0]["file_name"] == filename
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
