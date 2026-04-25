"""
@test_registry:
    suite: api-unit
    component: api.rag_collections (Sprint S / S144)
    covers:
        - src/aiflow/api/v1/rag_collections.py
    phase: sprint-s-s144
    priority: high
    estimated_duration_ms: 3000
    requires_services: []
    tags: [api, rag, collections, sprint-s, s144]
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider
from aiflow.services.rag_engine.service import CollectionInfo, DimensionMismatch


@contextmanager
def _client_and_headers() -> Iterator[tuple[TestClient, dict[str, str]]]:
    """Build app, client, and a matching admin Bearer token in one shot.

    Auth is provider-instance bound: a token only verifies on the same
    AuthProvider that signed it. ``AuthMiddleware.__init__`` runs lazily
    on the first request, not on ``create_app``, so the patch must stay
    active across both ``create_app`` AND the request — otherwise the
    middleware re-initialises against an unpatched ``from_env`` and the
    minted token verifies against a different key pair.
    """
    auth = AuthProvider.from_env()
    with patch.object(AuthProvider, "from_env", return_value=auth):
        from aiflow.api.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/health/live")  # warmup the middleware stack inside the patch
        token = auth.create_token(user_id="s144-test", role="admin")
        yield client, {"Authorization": f"Bearer {token}"}


def _coll(
    *,
    cid: str = "c-1",
    name: str = "coll-1",
    tenant_id: str = "default",
    profile: str | None = None,
    chunk_count: int = 0,
    embedding_dim: int = 1536,
) -> CollectionInfo:
    return CollectionInfo(
        id=cid,
        name=name,
        tenant_id=tenant_id,
        embedder_profile_id=profile,
        chunk_count=chunk_count,
        embedding_dim=embedding_dim,
    )


def _make_fake_service(**method_overrides: Any) -> Any:
    fake = AsyncMock()
    for k, v in method_overrides.items():
        setattr(fake, k, v)
    return fake


# ---------------------------------------------------------------------------
# GET / — tenant filter is honoured
# ---------------------------------------------------------------------------


def test_list_filters_by_tenant_id() -> None:
    fake = _make_fake_service(
        list_collections=AsyncMock(
            return_value=[
                _coll(cid="a", name="x", tenant_id="bestix"),
                _coll(cid="b", name="y", tenant_id="doha"),
                _coll(cid="c", name="z", tenant_id="bestix"),
            ]
        )
    )

    with (
        patch("aiflow.api.v1.rag_collections._get_service", AsyncMock(return_value=fake)),
        _client_and_headers() as (client, headers),
    ):
        resp = client.get("/api/v1/rag-collections?tenant_id=bestix", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    returned_ids = {item["id"] for item in body["items"]}
    assert returned_ids == {"a", "c"}
    assert all(item["tenant_id"] == "bestix" for item in body["items"])


# ---------------------------------------------------------------------------
# GET /{id} — 404 on missing
# ---------------------------------------------------------------------------


def test_detail_returns_404_when_missing() -> None:
    fake = _make_fake_service(get_collection=AsyncMock(return_value=None))

    with (
        patch("aiflow.api.v1.rag_collections._get_service", AsyncMock(return_value=fake)),
        _client_and_headers() as (client, headers),
    ):
        resp = client.get("/api/v1/rag-collections/nope", headers=headers)

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /{id}/embedder-profile — DimensionMismatch surfaces as HTTP 409
# ---------------------------------------------------------------------------


def test_patch_embedder_profile_surfaces_dim_mismatch_as_409() -> None:
    async def _raise_dim_mismatch(**_kwargs: Any) -> None:
        raise DimensionMismatch(
            "Cannot attach embedder_profile_id='bge_m3': embedding_dim=1536 vs 1024"
        )

    fake = _make_fake_service(set_embedder_profile=_raise_dim_mismatch)

    with (
        patch("aiflow.api.v1.rag_collections._get_service", AsyncMock(return_value=fake)),
        _client_and_headers() as (client, headers),
    ):
        resp = client.patch(
            "/api/v1/rag-collections/c-1/embedder-profile",
            json={"embedder_profile_id": "bge_m3"},
            headers=headers,
        )

    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["error_code"] == "RAG_DIM_MISMATCH"
    assert "1536" in detail["message"] and "1024" in detail["message"]
