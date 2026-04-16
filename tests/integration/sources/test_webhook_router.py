"""Integration tests for POST /api/v1/sources/webhook (Phase 1b — E2.3-B, Day 9).

@test_registry: phase_1b.sources.webhook_router

Composes a real ``ApiSourceAdapter`` with a deterministic clock behind the
FastAPI app, then exercises the full HTTP surface via ``TestClient``. Every
scenario signs the payload using the same helper as
``tests/unit/sources/test_api_adapter.py`` so the router and adapter stay in
lockstep on the signed-envelope format ``<timestamp>.<base64(body)>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from aiflow.api.app import create_app
from aiflow.api.v1.sources_webhook import (
    get_api_source_adapter,
    reset_api_source_adapter,
)
from aiflow.sources.api_adapter import ApiSourceAdapter

_SECRET = "integration-test-secret"
_NOW = 1_700_000_000


def _sign(secret: str, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "webhook-storage"


@pytest.fixture()
def adapter(storage_root: Path) -> ApiSourceAdapter:
    return ApiSourceAdapter(
        storage_root=storage_root,
        tenant_id="tenant_test",
        hmac_secret=_SECRET,
        max_clock_skew_seconds=300,
        max_package_bytes=1024,
        now=lambda: _NOW,
    )


@pytest.fixture()
def client(adapter: ApiSourceAdapter):
    # The factory reads AIFLOW_WEBHOOK_HMAC_SECRET eagerly only when the
    # default dependency is called; we override before any request.
    os.environ.setdefault("AIFLOW_WEBHOOK_HMAC_SECRET", "placeholder")
    reset_api_source_adapter()
    app = create_app()
    app.dependency_overrides[get_api_source_adapter] = lambda: adapter
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    reset_api_source_adapter()


# ---------------------------------------------------------------------------
# 1. Happy path — valid signature + timestamp → 202 + package_id UUID
# ---------------------------------------------------------------------------


def test_valid_signature_returns_202(client: TestClient) -> None:
    body = b"hello-webhook"
    ts = str(_NOW)
    sig = _sign(_SECRET, ts, body)
    resp = client.post(
        "/api/v1/sources/webhook",
        content=body,
        headers={
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
            "X-Filename": "hello.txt",
            "Content-Type": "text/plain",
        },
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["status"] == "accepted"
    # Must round-trip as a UUID.
    UUID(data["package_id"])


# ---------------------------------------------------------------------------
# 2. Invalid signature → 401
# ---------------------------------------------------------------------------


def test_invalid_signature_returns_401(client: TestClient) -> None:
    body = b"hello-webhook"
    ts = str(_NOW)
    resp = client.post(
        "/api/v1/sources/webhook",
        content=body,
        headers={
            "X-Webhook-Signature": "0" * 64,
            "X-Webhook-Timestamp": ts,
            "X-Filename": "hello.txt",
        },
    )
    assert resp.status_code == 401, resp.text
    # Secret must never leak in the response body.
    assert _SECRET not in resp.text


# ---------------------------------------------------------------------------
# 3. Expired timestamp → 401 (outside replay window)
# ---------------------------------------------------------------------------


def test_expired_timestamp_returns_401(client: TestClient) -> None:
    body = b"old"
    ts = str(_NOW - 3600)  # 1h ago — well beyond 5min window
    sig = _sign(_SECRET, ts, body)
    resp = client.post(
        "/api/v1/sources/webhook",
        content=body,
        headers={
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
            "X-Filename": "old.txt",
        },
    )
    assert resp.status_code == 401, resp.text
    assert "replay" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Duplicate Idempotency-Key → 409
# ---------------------------------------------------------------------------


def test_duplicate_idempotency_key_returns_409(client: TestClient) -> None:
    body = b"idem-body"
    ts = str(_NOW)
    sig = _sign(_SECRET, ts, body)
    headers = {
        "X-Webhook-Signature": sig,
        "X-Webhook-Timestamp": ts,
        "X-Filename": "idem.txt",
        "Idempotency-Key": "test-key-42",
    }
    first = client.post("/api/v1/sources/webhook", content=body, headers=headers)
    assert first.status_code == 202, first.text

    second = client.post("/api/v1/sources/webhook", content=body, headers=headers)
    assert second.status_code == 409, second.text
    assert "duplicate" in second.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Oversized body → 413 (adapter-level max_package_bytes=1024)
# ---------------------------------------------------------------------------


def test_oversized_body_returns_413(client: TestClient) -> None:
    body = b"x" * 2048
    ts = str(_NOW)
    sig = _sign(_SECRET, ts, body)
    resp = client.post(
        "/api/v1/sources/webhook",
        content=body,
        headers={
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
            "X-Filename": "big.bin",
        },
    )
    assert resp.status_code == 413, resp.text
    assert "max_package_bytes" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Missing X-Filename → 422 (FastAPI header validation) — we accept
# either 400 or 422 to keep the test resilient to FastAPI behavior.
# ---------------------------------------------------------------------------


def test_missing_filename_header_rejected(client: TestClient) -> None:
    body = b"nofile"
    ts = str(_NOW)
    sig = _sign(_SECRET, ts, body)
    resp = client.post(
        "/api/v1/sources/webhook",
        content=body,
        headers={
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
        },
    )
    assert resp.status_code in (400, 422), resp.text


# ---------------------------------------------------------------------------
# 7. Missing X-Webhook-Signature → 401
# ---------------------------------------------------------------------------


def test_missing_signature_header_returns_401(client: TestClient) -> None:
    body = b"no-sig"
    ts = str(_NOW)
    resp = client.post(
        "/api/v1/sources/webhook",
        content=body,
        headers={
            "X-Webhook-Timestamp": ts,
            "X-Filename": "nosig.txt",
        },
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# 8. OpenAPI schema contains the endpoint + 4xx responses
# ---------------------------------------------------------------------------


def test_openapi_schema_documents_webhook_contract(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    path = schema["paths"].get("/api/v1/sources/webhook")
    assert path is not None, "webhook endpoint missing from OpenAPI"
    post = path["post"]
    responses = post["responses"]
    # Must document all 4xx variants plus the 202 success.
    for code in ("202", "400", "401", "409", "413"):
        assert code in responses, f"{code} response missing"
    # Header params surfaced for SDK generators.
    param_names = {p.get("name") for p in post.get("parameters", [])}
    assert "X-Webhook-Signature" in param_names
    assert "X-Webhook-Timestamp" in param_names
    assert "X-Filename" in param_names
    # Secret must never appear in the schema.
    assert _SECRET not in resp.text
