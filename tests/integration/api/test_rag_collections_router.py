"""Integration test — /api/v1/rag-collections live admin surface.

@test_registry
suite: integration-api
component: api.v1.rag_collections (Sprint S / S144)
covers:
    - src/aiflow/api/v1/rag_collections.py
    - src/aiflow/services/rag_engine/service.py
    - alembic/versions/046_rag_collections_tenant_embedder_profile.py
phase: v1.5.2
priority: critical
requires_services: [postgres]
tags: [integration, api, rag_engine, rag_collections, sprint_s, s144, postgres]

Exercises the GET list with tenant filter, the PATCH …/embedder-profile
mutation on an empty collection, and the DimensionMismatch (HTTP 409)
guard against real Docker PostgreSQL (port 5433).

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop
bound — DB seeds/cleanups use a fresh asyncpg connection, never the
app's pool. All assertions for one tenant happen inside one TestClient.
"""

from __future__ import annotations

import asyncio
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


def _headers() -> dict[str, str]:
    token = _shared_auth.create_token(user_id="s144-admin", role="admin", team_id="default")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_pair() -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return f"s144-{suffix}-bestix", f"s144-{suffix}-doha"


async def _seed_collection(
    *,
    name: str,
    tenant: str,
    embedder_profile_id: str | None,
    embedding_dim: int,
    chunk_count: int = 0,
) -> str:
    conn = await asyncpg.connect(_db_url())
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO rag_collections
                (id, name, customer, skill_name,
                 tenant_id, embedder_profile_id, embedding_dim, chunk_count)
            VALUES (gen_random_uuid(), $1, $2, 'rag_engine', $3, $4, $5, $6)
            RETURNING id
            """,
            name,
            tenant,
            tenant,
            embedder_profile_id,
            embedding_dim,
            chunk_count,
        )
        return str(row["id"])
    finally:
        await conn.close()


async def _read_collection_profile(collection_id: str) -> tuple[str | None, int]:
    conn = await asyncpg.connect(_db_url())
    try:
        row = await conn.fetchrow(
            "SELECT embedder_profile_id, embedding_dim FROM rag_collections WHERE id = $1",
            uuid.UUID(collection_id),
        )
        if row is None:
            raise AssertionError(f"row {collection_id} disappeared")
        return row["embedder_profile_id"], int(row["embedding_dim"])
    finally:
        await conn.close()


async def _cleanup(tenant_ids: tuple[str, ...]) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        for t in tenant_ids:
            await conn.execute("DELETE FROM rag_collections WHERE tenant_id = $1", t)
    finally:
        await conn.close()


def test_list_filters_by_tenant_id(client: TestClient, tenant_pair: tuple[str, str]) -> None:
    """Two collections in two tenants → list filtered to one of them returns only that row."""
    bestix, doha = tenant_pair
    try:
        c_bestix = asyncio.run(
            _seed_collection(
                name=f"{bestix}-coll",
                tenant=bestix,
                embedder_profile_id=None,
                embedding_dim=1536,
            )
        )
        c_doha = asyncio.run(
            _seed_collection(
                name=f"{doha}-coll",
                tenant=doha,
                embedder_profile_id="bge_m3",
                embedding_dim=1024,
            )
        )

        # Filtered to bestix — exactly one row, exactly the bestix collection.
        r = client.get(f"/api/v1/rag-collections?tenant_id={bestix}", headers=_headers())
        assert r.status_code == 200, r.text
        body = r.json()
        ids = [item["id"] for item in body["items"]]
        assert ids == [c_bestix]
        assert body["items"][0]["tenant_id"] == bestix
        assert body["items"][0]["embedder_profile_id"] is None
        assert body["items"][0]["embedding_dim"] == 1536

        # Filtered to doha — exactly the doha collection with its 1024-dim profile.
        r2 = client.get(f"/api/v1/rag-collections?tenant_id={doha}", headers=_headers())
        assert r2.status_code == 200
        body2 = r2.json()
        ids2 = [item["id"] for item in body2["items"]]
        assert ids2 == [c_doha]
        assert body2["items"][0]["embedder_profile_id"] == "bge_m3"
        assert body2["items"][0]["embedding_dim"] == 1024
    finally:
        asyncio.run(_cleanup(tenant_pair))


def test_patch_embedder_profile_on_empty_collection_persists(
    client: TestClient, tenant_pair: tuple[str, str]
) -> None:
    """PATCH on an empty collection updates embedder_profile_id (and embedding_dim)."""
    bestix, _ = tenant_pair
    try:
        cid = asyncio.run(
            _seed_collection(
                name=f"{bestix}-empty",
                tenant=bestix,
                embedder_profile_id=None,
                embedding_dim=1536,
                chunk_count=0,
            )
        )

        r = client.patch(
            f"/api/v1/rag-collections/{cid}/embedder-profile",
            json={"embedder_profile_id": "openai"},
            headers=_headers(),
        )
        # OpenAIEmbedder may need an env key — accept either a clean 200 path
        # or a DimensionMismatch-wrapped instantiation failure (still a guard
        # outcome that proves the endpoint reached the service layer).
        if r.status_code == 200:
            body = r.json()
            assert body["embedder_profile_id"] == "openai"
            db_profile, db_dim = asyncio.run(_read_collection_profile(cid))
            assert db_profile == "openai"
            # OpenAIEmbedder dim is 1536 → embedding_dim unchanged.
            assert db_dim == 1536
        else:
            # If the real OpenAI embedder couldn't initialize (e.g., no creds),
            # the service raises DimensionMismatch on probe failure.
            assert r.status_code == 409, r.text

        # Detach (→ NULL) — must succeed because the collection is empty (or
        # was empty even after a possible profile attach in the 200 branch).
        r2 = client.patch(
            f"/api/v1/rag-collections/{cid}/embedder-profile",
            json={"embedder_profile_id": None},
            headers=_headers(),
        )
        assert r2.status_code == 200, r2.text
        db_profile_after, _ = asyncio.run(_read_collection_profile(cid))
        assert db_profile_after is None
    finally:
        asyncio.run(_cleanup(tenant_pair))


def test_patch_dim_mismatch_returns_409_and_does_not_mutate(
    client: TestClient, tenant_pair: tuple[str, str]
) -> None:
    """A populated 1536-dim collection cannot accept a 1024-dim profile."""
    bestix, _ = tenant_pair
    try:
        cid = asyncio.run(
            _seed_collection(
                name=f"{bestix}-populated",
                tenant=bestix,
                embedder_profile_id=None,
                embedding_dim=1536,
                chunk_count=42,
            )
        )

        # bge_m3 is 1024-dim; collection is 1536-dim populated → must 409.
        # We can't probe the real BGE-M3 model in CI, so we monkeypatch the
        # provider class to a stub that reports dim=1024.
        from aiflow.providers import embedder as _embedder_mod

        class _BGEM3Stub:
            PROVIDER_NAME = "bge_m3"

            def __init__(self) -> None:
                pass

            @property
            def embedding_dim(self) -> int:
                return 1024

            @property
            def model_name(self) -> str:
                return "stub/bge-m3"

        original = _embedder_mod.BGEM3Embedder
        _embedder_mod.BGEM3Embedder = _BGEM3Stub  # type: ignore[misc]
        try:
            r = client.patch(
                f"/api/v1/rag-collections/{cid}/embedder-profile",
                json={"embedder_profile_id": "bge_m3"},
                headers=_headers(),
            )
        finally:
            _embedder_mod.BGEM3Embedder = original  # type: ignore[misc]

        assert r.status_code == 409, r.text
        assert r.json()["detail"]["error_code"] == "RAG_DIM_MISMATCH"

        # DB row was NOT touched.
        db_profile, db_dim = asyncio.run(_read_collection_profile(cid))
        assert db_profile is None
        assert db_dim == 1536
    finally:
        asyncio.run(_cleanup(tenant_pair))
