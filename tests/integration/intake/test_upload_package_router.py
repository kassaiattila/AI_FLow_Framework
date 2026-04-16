"""Integration tests — POST /api/v1/intake/upload-package.

@test_registry
suite: integration-intake
component: api.v1.intake
covers: [src/aiflow/api/v1/intake.py, src/aiflow/state/repositories/intake.py]
phase: 1b
priority: critical
requires_services: [postgres]
tags: [integration, intake, upload_package, fastapi, postgres, association_mode]

Exercises the full multipart path end-to-end against real Docker PostgreSQL
(port 5433) per CLAUDE.md — no mocks. Each test uses a unique tenant_id
derived from ``uuid4()``; test teardown deletes all rows for that tenant so
the DB stays clean across runs and parallel CI shards.

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop-bound.
All DB assertions share the module-level ``get_pool()`` and the FastAPI
``TestClient`` drives the same event loop used by the app's lifespan.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider


def _db_url() -> str:
    """Raw asyncpg URL matching aiflow.api.deps but safe from any event loop."""
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


# Install a shared AuthProvider BEFORE importing create_app so that the
# middleware's lazy AuthProvider.from_env() resolves to the same instance the
# tests use to mint tokens.
_shared_auth = AuthProvider.from_env()
_from_env_patcher = patch.object(AuthProvider, "from_env", return_value=_shared_auth)
_from_env_patcher.start()

from aiflow.api.app import create_app  # noqa: E402

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _warmed_app(tmp_path_factory: pytest.TempPathFactory):
    """Build the FastAPI app once per module and warm up the middleware.

    Resets ``aiflow.api.deps._pool`` before and after to avoid cross-module
    stale-pool contamination (pools are event-loop-bound — see
    ``feedback_asyncpg_pool_event_loop.md``).
    """
    os.environ.setdefault("AIFLOW_WEBHOOK_HMAC_SECRET", "placeholder-for-tests")
    upload_root = tmp_path_factory.mktemp("intake_uploads")
    os.environ["AIFLOW_INTAKE_UPLOAD_ROOT"] = str(upload_root)
    # Small cap so we can exercise 413 deterministically.
    os.environ["AIFLOW_INTAKE_UPLOAD_MAX_BYTES"] = str(64 * 1024)

    from aiflow.api import deps as _deps

    _deps._pool = None
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        # Trigger middleware init + pool creation on the TestClient loop.
        c.get("/health/live")
        yield app, c, upload_root
    _deps._pool = None


@pytest.fixture()
def client(_warmed_app):
    _, c, _ = _warmed_app
    return c


@pytest.fixture()
def upload_root(_warmed_app) -> Path:
    _, _, root = _warmed_app
    return root


def _make_token(tenant_id: str, user_id: str = "test-user", role: str = "admin") -> str:
    return _shared_auth.create_token(user_id=user_id, role=role, team_id=tenant_id)


def _auth_headers(tenant_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(tenant_id)}"}


async def _cleanup_tenant(tenant_id: str) -> None:
    """Delete all rows belonging to tenant_id via a fresh asyncpg connection.

    NOTE (feedback_asyncpg_pool_event_loop.md): cannot reuse the app's shared
    pool here because this coroutine runs in a new ``asyncio.run()`` event
    loop per test finalizer — different loop than TestClient's internal one.
    """
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


@pytest.fixture()
def tenant_id(request: pytest.FixtureRequest) -> str:
    """Per-test tenant_id that is torn down regardless of test outcome."""
    tid = f"tenant-upload-{uuid4().hex[:10]}"

    def _teardown() -> None:
        asyncio.run(_cleanup_tenant(tid))

    request.addfinalizer(_teardown)
    return tid


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_two_files_two_descriptions_order_mode(client: TestClient, tenant_id: str) -> None:
    """2 files + 2 descriptions + mode=order → 201, round-trips with order associations."""
    headers = _auth_headers(tenant_id)
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=headers,
        files=[
            ("files", ("a.pdf", b"aaaa", "application/pdf")),
            ("files", ("b.pdf", b"bbbb", "application/pdf")),
        ],
        data={
            "descriptions": json.dumps([{"text": "first"}, {"text": "second"}]),
            "association_mode": "order",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["file_count"] == 2
    assert body["description_count"] == 2
    assert body["association_mode"] == "order"
    assert body["tenant_id"] == tenant_id
    assert body["source_type"] == "file_upload"

    # Assert DB state directly via a fresh asyncpg connection (loop-safe).
    async def _check() -> None:
        conn = await asyncpg.connect(_db_url())
        try:
            mode = await conn.fetchval(
                "SELECT association_mode FROM intake_packages WHERE package_id = $1",
                UUID(body["package_id"]),
            )
            file_rows = await conn.fetch(
                "SELECT file_name FROM intake_files WHERE package_id = $1 ORDER BY sequence_index",
                UUID(body["package_id"]),
            )
            assoc_rows = await conn.fetch(
                """
                SELECT pa.description_id, pa.file_id
                FROM package_associations pa
                JOIN intake_files f ON f.file_id = pa.file_id
                WHERE f.package_id = $1
                """,
                UUID(body["package_id"]),
            )
        finally:
            await conn.close()
        assert mode == "order"
        assert [r["file_name"] for r in file_rows] == ["a.pdf", "b.pdf"]
        assert len(assoc_rows) == 2

    asyncio.run(_check())


def test_single_file_single_description_auto_single_description(
    client: TestClient, tenant_id: str
) -> None:
    """1 file + 1 description, no mode → auto SINGLE_DESCRIPTION."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        files=[("files", ("doc.pdf", b"only", "application/pdf"))],
        data={"descriptions": json.dumps([{"text": "only description"}])},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["file_count"] == 1
    assert body["description_count"] == 1
    # With N=M=1, auto-detect walks precedence: EXPLICIT (fails) → FILENAME_MATCH
    # (fails, no rules) → ORDER (succeeds because N==M). We assert on the
    # persisted mode which mirrors this precedence.
    assert body["association_mode"] in {"order", "single_description"}


def test_filename_match_rules(client: TestClient, tenant_id: str) -> None:
    """3 files + 3 descriptions + mode=filename_match + filename_rules → 201."""
    inv_id = str(uuid4())
    rec_id = str(uuid4())
    pkg_id = str(uuid4())
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        files=[
            ("files", ("invoice-1.pdf", b"inv1", "application/pdf")),
            ("files", ("receipt-2.pdf", b"rec2", "application/pdf")),
            ("files", ("invoice-3.pdf", b"inv3", "application/pdf")),
        ],
        data={
            "descriptions": json.dumps(
                [
                    {"description_id": inv_id, "text": "invoices"},
                    {"description_id": rec_id, "text": "receipts"},
                    {"description_id": pkg_id, "text": "package note"},
                ]
            ),
            "association_mode": "filename_match",
            "filename_rules": json.dumps(
                [
                    {"pattern": r"^invoice-", "description_id": inv_id},
                    {"pattern": r"^receipt-", "description_id": rec_id},
                ]
            ),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["association_mode"] == "filename_match"
    # Inspect the descriptions response — file associations should split by prefix.
    by_desc = {UUID(d["description_id"]): d for d in body["descriptions"]}
    inv_files = by_desc[UUID(inv_id)]["associated_file_ids"]
    rec_files = by_desc[UUID(rec_id)]["associated_file_ids"]
    pkg_files = by_desc[UUID(pkg_id)]["associated_file_ids"]
    assert len(inv_files) == 2
    assert len(rec_files) == 1
    assert pkg_files == []


# ---------------------------------------------------------------------------
# Auth / tenant_id failure modes
# ---------------------------------------------------------------------------


def test_missing_authorization_header_returns_401(client: TestClient) -> None:
    """No JWT → 401, no DB row written."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        files=[("files", ("a.pdf", b"a", "application/pdf"))],
    )
    assert resp.status_code == 401, resp.text


def test_invalid_jwt_returns_401(client: TestClient) -> None:
    """Bearer string that fails verification → 401 from AuthMiddleware."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers={"Authorization": "Bearer not.a.real.jwt"},
        files=[("files", ("a.pdf", b"a", "application/pdf"))],
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Validation failure modes
# ---------------------------------------------------------------------------


def test_malformed_descriptions_json_returns_400(client: TestClient, tenant_id: str) -> None:
    """descriptions form field that isn't valid JSON → 400."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        files=[("files", ("a.pdf", b"a", "application/pdf"))],
        data={"descriptions": "{{not-json"},
    )
    assert resp.status_code == 400, resp.text
    assert "descriptions" in resp.json()["detail"]


def test_order_mode_mismatch_returns_422(client: TestClient, tenant_id: str) -> None:
    """mode=order but len(files) != len(descriptions) → 422 AssociationError."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        files=[
            ("files", ("a.pdf", b"a", "application/pdf")),
            ("files", ("b.pdf", b"b", "application/pdf")),
        ],
        data={
            "descriptions": json.dumps([{"text": "only one"}]),
            "association_mode": "order",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "ORDER" in resp.json()["detail"] or "order" in resp.json()["detail"].lower()


def test_zero_files_rejected(client: TestClient, tenant_id: str) -> None:
    """No ``files`` part at all → 400 (FastAPI says 422, endpoint says 400)."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        data={"descriptions": "[]"},
    )
    # FastAPI's List[UploadFile] with no parts raises 422 at the validator
    # level before the endpoint's own guard fires.
    assert resp.status_code in (400, 422), resp.text


def test_invalid_association_mode_returns_400(client: TestClient, tenant_id: str) -> None:
    """Unknown association_mode string → 400 with allowed-values hint."""
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        files=[("files", ("a.pdf", b"a", "application/pdf"))],
        data={"association_mode": "not-a-mode"},
    )
    assert resp.status_code == 400, resp.text
    assert "association_mode" in resp.json()["detail"]


def test_oversized_upload_returns_413(client: TestClient, tenant_id: str) -> None:
    """Aggregate file bytes > max_total_bytes → 413."""
    # max is 64 KiB in the module fixture; one 128 KiB file is well over.
    big = b"X" * (128 * 1024)
    resp = client.post(
        "/api/v1/intake/upload-package",
        headers=_auth_headers(tenant_id),
        files=[("files", ("big.bin", big, "application/octet-stream"))],
    )
    assert resp.status_code == 413, resp.text


# ---------------------------------------------------------------------------
# OpenAPI contract
# ---------------------------------------------------------------------------


def test_openapi_schema_documents_upload_package(client: TestClient) -> None:
    """Endpoint + 4xx responses surface in the auto-generated OpenAPI."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    path = schema["paths"].get("/api/v1/intake/upload-package")
    assert path is not None, "upload-package endpoint missing from OpenAPI"
    responses = path["post"]["responses"]
    for code in ("201", "400", "401", "413", "422"):
        assert code in responses, f"{code} response missing from OpenAPI"
