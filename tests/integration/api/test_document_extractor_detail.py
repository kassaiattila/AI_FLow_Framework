"""Integration tests — GET /api/v1/document-extractor/packages/{id}.

@test_registry
suite: integration-api
component: api.v1.document_extractor
covers: [src/aiflow/api/v1/document_extractor.py]
phase: 1.4.5
priority: high
requires_services: [postgres]
tags: [integration, document_extractor, viewer, s97]

Exercises the S97 UC1 viewer endpoint against real Docker PostgreSQL
(port 5433). Every test seeds its own tenant-scoped rows and tears them
down regardless of outcome.

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop
bound — DB assertions use a fresh connection, never the app's pool.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from unittest.mock import patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider


def _db_url() -> str:
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


_shared_auth = AuthProvider.from_env()

from aiflow.api.app import create_app  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def _patch_auth_from_env():
    with patch.object(AuthProvider, "from_env", return_value=_shared_auth):
        yield


@pytest.fixture(scope="module")
def client():
    from aiflow.api import deps as _deps

    _deps._pool = None
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.get("/health/live")
        yield c
    _deps._pool = None


def _headers(tenant_id: str) -> dict[str, str]:
    token = _shared_auth.create_token(user_id="test-user", role="admin", team_id=tenant_id)
    return {"Authorization": f"Bearer {token}"}


async def _seed_package(
    tenant_id: str,
    *,
    with_routing: bool = True,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a minimal intake_packages/intake_files/routing_decisions row set."""
    package_id = uuid.uuid4()
    file_id = uuid.uuid4()
    conn = await asyncpg.connect(_db_url())
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO intake_packages (
                    package_id, source_type, tenant_id, status,
                    source_metadata, package_context, cross_document_signals
                ) VALUES ($1, 'file_upload', $2, 'received', '{}', '{}', '{}')
                """,
                package_id,
                tenant_id,
            )
            await conn.execute(
                """
                INSERT INTO intake_files (
                    file_id, package_id, file_path, file_name,
                    mime_type, size_bytes, sha256, sequence_index
                ) VALUES ($1, $2, '/tmp/fake.pdf', 'fake.pdf',
                          'application/pdf', 2048,
                          '0000000000000000000000000000000000000000000000000000000000000000',
                          0)
                """,
                file_id,
                package_id,
            )
            if with_routing:
                await conn.execute(
                    """
                    INSERT INTO routing_decisions (
                        package_id, file_id, tenant_id,
                        chosen_parser, reason, signals, fallback_chain, cost_estimate
                    ) VALUES ($1, $2, $3,
                              'docling_standard', 'local_ok_default_parser',
                              $4::jsonb, $5::jsonb, 0)
                    """,
                    package_id,
                    file_id,
                    tenant_id,
                    json.dumps({"size_bytes": 2048, "mime_type": "application/pdf"}),
                    json.dumps(["unstructured_fast"]),
                )
    finally:
        await conn.close()
    return package_id, file_id


async def _cleanup_tenant(tenant_id: str) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM routing_decisions WHERE tenant_id = $1",
                tenant_id,
            )
            pkg_ids = [
                r["package_id"]
                for r in await conn.fetch(
                    "SELECT package_id FROM intake_packages WHERE tenant_id = $1",
                    tenant_id,
                )
            ]
            if pkg_ids:
                await conn.execute(
                    "DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])",
                    pkg_ids,
                )
                await conn.execute(
                    "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])",
                    pkg_ids,
                )
    finally:
        await conn.close()


@pytest.fixture()
def tenant_id(request: pytest.FixtureRequest) -> str:
    tid = f"tenant-docext-{uuid.uuid4().hex[:10]}"

    def _teardown() -> None:
        asyncio.run(_cleanup_tenant(tid))

    request.addfinalizer(_teardown)
    return tid


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_get_package_detail_happy_path(client: TestClient, tenant_id: str) -> None:
    package_id, file_id = asyncio.run(_seed_package(tenant_id))

    resp = client.get(
        f"/api/v1/document-extractor/packages/{package_id}",
        headers=_headers(tenant_id),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["package_id"] == str(package_id)
    assert body["tenant_id"] == tenant_id
    assert body["source_type"] == "file_upload"
    assert body["files"] and body["files"][0]["file_id"] == str(file_id)
    assert body["routing_decisions"]
    decision = body["routing_decisions"][0]
    assert decision["chosen_parser"] == "docling_standard"
    assert decision["signals"]["size_bytes"] == 2048
    assert decision["fallback_chain"] == ["unstructured_fast"]
    # extraction persistence is deferred to S97.5 — must be an empty list now.
    assert body["extractions"] == []


# ---------------------------------------------------------------------------
# 404 paths
# ---------------------------------------------------------------------------


def test_get_package_detail_unknown_id_404(client: TestClient, tenant_id: str) -> None:
    resp = client.get(
        f"/api/v1/document-extractor/packages/{uuid.uuid4()}",
        headers=_headers(tenant_id),
    )
    assert resp.status_code == 404


def test_get_package_detail_cross_tenant_is_404(client: TestClient, tenant_id: str) -> None:
    """Cross-tenant access must surface as 404 (never 403) to avoid leaking ids."""
    package_id, _ = asyncio.run(_seed_package(tenant_id))

    other_tenant = f"tenant-other-{uuid.uuid4().hex[:8]}"
    try:
        resp = client.get(
            f"/api/v1/document-extractor/packages/{package_id}",
            headers=_headers(other_tenant),
        )
        assert resp.status_code == 404
    finally:
        asyncio.run(_cleanup_tenant(other_tenant))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_get_package_detail_requires_auth(client: TestClient) -> None:
    resp = client.get(f"/api/v1/document-extractor/packages/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)
