"""E2E — POST /api/v1/intake/upload-package (Week 3 Day 13 / E3.2).

@test_registry
suite: phase_1b_e2e
component: api.v1.intake
covers: [src/aiflow/api/v1/intake.py]
phase: 1b
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1b, intake, upload_package]

Reuses the integration harness against the real FastAPI app with real
Postgres (port 5433) — no mocks. These tests pin the external contract of
the multipart upload endpoint from the caller's perspective.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch
from uuid import UUID, uuid4

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
_from_env_patcher = patch.object(AuthProvider, "from_env", return_value=_shared_auth)
_from_env_patcher.start()

from aiflow.api.app import create_app  # noqa: E402

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def _warmed_app(tmp_path_factory: pytest.TempPathFactory):
    os.environ.setdefault("AIFLOW_WEBHOOK_HMAC_SECRET", "placeholder-for-tests")
    upload_root = tmp_path_factory.mktemp("e2e_intake_uploads")
    os.environ["AIFLOW_INTAKE_UPLOAD_ROOT"] = str(upload_root)

    from aiflow.api import deps as _deps

    # Reset the module-level pool so it gets re-created on TestClient's loop
    # (asyncpg pools are loop-bound — feedback_asyncpg_pool_event_loop.md).
    _deps._pool = None
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.get("/health/live")
        yield c
    _deps._pool = None


@pytest.fixture()
def client(_warmed_app):
    return _warmed_app


def _make_token(tenant_id: str) -> str:
    return _shared_auth.create_token(user_id="e2e-user", role="admin", team_id=tenant_id)


async def _cleanup_tenant(tenant_id: str) -> None:
    """Fresh asyncpg connection — cannot reuse app pool across loops."""
    conn = await asyncpg.connect(_db_url())
    try:
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
    finally:
        await conn.close()


def test_upload_package_multipart_creates_intake_package(client: TestClient) -> None:
    """Multipart upload (N files + M descriptions + association_mode) → 201 + summary."""
    tenant_id = f"tenant-e2e-up-{uuid4().hex[:10]}"
    try:
        resp = client.post(
            "/api/v1/intake/upload-package",
            headers={"Authorization": f"Bearer {_make_token(tenant_id)}"},
            files=[
                ("files", ("one.pdf", b"first-bytes", "application/pdf")),
                ("files", ("two.pdf", b"second-bytes", "application/pdf")),
            ],
            data={
                "descriptions": json.dumps([{"text": "first note"}, {"text": "second note"}]),
                "association_mode": "order",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["tenant_id"] == tenant_id
        assert body["source_type"] == "file_upload"
        assert body["file_count"] == 2
        assert body["description_count"] == 2
        assert body["association_mode"] == "order"
        # Response summary does not leak absolute file paths.
        for f in body["files"]:
            assert "file_path" not in f

        async def _db_check() -> None:
            conn = await asyncpg.connect(_db_url())
            try:
                mode = await conn.fetchval(
                    "SELECT association_mode FROM intake_packages WHERE package_id = $1",
                    UUID(body["package_id"]),
                )
                assoc_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM package_associations pa
                    JOIN intake_files f ON f.file_id = pa.file_id
                    WHERE f.package_id = $1
                    """,
                    UUID(body["package_id"]),
                )
            finally:
                await conn.close()
            assert mode == "order"
            assert assoc_count == 2

        asyncio.run(_db_check())
    finally:
        asyncio.run(_cleanup_tenant(tenant_id))


def test_upload_package_rejects_missing_tenant(client: TestClient) -> None:
    """Missing Authorization header → 401, no package created."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        files=[("files", ("a.pdf", b"a", "application/pdf"))],
    )
    assert resp.status_code == 401, resp.text
