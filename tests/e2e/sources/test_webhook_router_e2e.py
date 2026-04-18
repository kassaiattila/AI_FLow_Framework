"""E2E — POST /api/v1/sources/webhook → IntakePackageSink → real PostgreSQL (Phase 1d G0.6).

@test_registry
suite: phase_1d_e2e
component: api.v1.sources_webhook, sources.api_adapter, sources.sink,
           state.repositories.intake
covers:
    - src/aiflow/api/v1/sources_webhook.py
    - src/aiflow/sources/api_adapter.py
    - src/aiflow/sources/sink.py
phase: 1d
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1d, webhook, sink, postgres, http]

Validates the G0.6 deliverable: the webhook router's Path A refactor wires
``ApiSourceAdapter.enqueue()`` directly into ``IntakePackageSink.handle()``
so the HTTP-accepted package is durably persisted before the response
returns. Status 202 → 201 because the route now creates the resource
synchronously (not just queues it).

Two cases in one method (asyncpg pool + event loop trap — see
feedback_asyncpg_pool_event_loop.md): a happy-path 201 with DB round-trip
+ one negative (invalid signature → 401, no DB row).

NOTE: the webhook endpoint is registered under ``_PUBLIC_PREFIXES`` in
``aiflow.api.middleware`` so HMAC verification replaces bearer/API-key
auth. No JWT header needed.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aiflow.api import deps as _deps
from aiflow.api.v1.sources_webhook import (
    get_api_source_adapter,
    reset_api_source_adapter,
)
from aiflow.security.auth import AuthProvider
from aiflow.sources.api_adapter import ApiSourceAdapter

_SECRET = "G0.6-webhook-e2e-secret"
_FIXED_NOW = 1_700_700_000


def _sign(secret: str, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _db_url() -> str:
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


_shared_auth = AuthProvider.from_env()
_from_env_patcher = patch.object(AuthProvider, "from_env", return_value=_shared_auth)
_from_env_patcher.start()

from aiflow.api.app import create_app  # noqa: E402


async def _cleanup_tenant(tenant_id: str) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1", tenant_id
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM package_associations
                WHERE file_id IN (SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[]))
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
    finally:
        await conn.close()


@pytest.fixture()
def tenant_id() -> str:
    return f"tenant-G0.6-webhook-{uuid4().hex[:10]}"


@pytest.fixture()
def adapter(tmp_path: Path, tenant_id: str) -> ApiSourceAdapter:
    return ApiSourceAdapter(
        storage_root=tmp_path / "webhook_e2e_storage",
        tenant_id=tenant_id,
        hmac_secret=_SECRET,
        max_clock_skew_seconds=300,
        now=lambda: _FIXED_NOW,
    )


@pytest.fixture()
def client(adapter: ApiSourceAdapter, tenant_id: str) -> Iterator[TestClient]:
    os.environ.setdefault("AIFLOW_WEBHOOK_HMAC_SECRET", "placeholder-for-tests")
    reset_api_source_adapter()
    _deps._pool = None
    app = create_app()
    app.dependency_overrides[get_api_source_adapter] = lambda: adapter
    with TestClient(app, raise_server_exceptions=False) as c:
        c.get("/health/live")
        yield c
    app.dependency_overrides.clear()
    reset_api_source_adapter()
    _deps._pool = None
    asyncio.run(_cleanup_tenant(tenant_id))


def test_webhook_persists_through_sink_to_postgres(client: TestClient, tenant_id: str) -> None:
    payload = b"%PDF-1.4\nG0.6 webhook fixture\n"
    ts = str(_FIXED_NOW)
    sig = _sign(_SECRET, ts, payload)

    resp = client.post(
        "/api/v1/sources/webhook",
        content=payload,
        headers={
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
            "X-Filename": "g06_webhook.pdf",
            "Content-Type": "application/pdf",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    package_id = UUID(body["package_id"])
    assert body["status"] == "accepted"

    async def _db_check() -> None:
        conn = await asyncpg.connect(_db_url())
        try:
            row = await conn.fetchrow(
                """
                SELECT package_id, source_type, tenant_id, association_mode
                FROM intake_packages
                WHERE package_id = $1
                """,
                package_id,
            )
            assert row is not None, "webhook returned 201 but DB row missing"
            assert row["source_type"] == "api_push"
            assert row["tenant_id"] == tenant_id
            # No descriptions on Api adapter → mode stays NULL.
            assert row["association_mode"] is None

            file_count = await conn.fetchval(
                "SELECT COUNT(*) FROM intake_files WHERE package_id = $1", package_id
            )
            assert file_count == 1
        finally:
            await conn.close()

    asyncio.run(_db_check())


def test_webhook_invalid_signature_does_not_persist(client: TestClient, tenant_id: str) -> None:
    payload = b"%PDF-1.4\nshould not be persisted\n"
    ts = str(_FIXED_NOW)

    resp = client.post(
        "/api/v1/sources/webhook",
        content=payload,
        headers={
            "X-Webhook-Signature": "0" * 64,
            "X-Webhook-Timestamp": ts,
            "X-Filename": "evil.pdf",
        },
    )
    assert resp.status_code == 401, resp.text

    async def _db_check() -> None:
        conn = await asyncpg.connect(_db_url())
        try:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM intake_packages WHERE tenant_id = $1", tenant_id
            )
            assert count == 0, f"invalid signature must not persist (count={count})"
        finally:
            await conn.close()

    asyncio.run(_db_check())
