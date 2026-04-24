"""UC2 RAG query-path ProviderRegistry — 1024-dim BGE-M3 queryable.

@test_registry
suite: integration_services_rag_engine
component: aiflow.services.rag_engine.service
covers: [src/aiflow/services/rag_engine/service.py]
phase: v1.5.2
priority: high
requires_services: [postgres]
tags: [integration, services, rag_engine, query, provider_registry, sprint_s, s143, bge_m3]

Sprint S / S143 — closes Sprint J FU-1. Functional proof that a RAG
collection pinned to ``embedder_profile_id='bge_m3'`` (1024-dim) is
end-to-end queryable now that ``RAGEngineService.query()`` resolves the
embedder through the ProviderRegistry adapter instead of the hardcoded
``self._embedder``.

Scope of this test (minimal, no LLM round-trip):

1. Seed a ``rag_collections`` row with ``embedder_profile_id='bge_m3'``,
   ``embedding_dim=1024``.
2. Instantiate the resolver on a synthetic ``RAGEngineService`` and prove
   it returns a ``_QueryEmbedderAdapter`` over a real ``BGEM3Embedder``.
3. Call ``adapter.embed_query('<hu question>')`` — assert a 1024-dim
   float vector comes back (the functional unblock).
4. Upsert a single 1024-dim chunk into ``rag_chunks`` via the real
   ``PgVectorStore`` (flex-dim column, migration 042) and assert
   ``search()`` retrieves it when given the real query vector.

LLM generation is intentionally out of scope — it would require an
OPENAI_API_KEY the CI image does not have, and the S143 goal is the
retrieval unblock, not answer quality. Answer quality lives in
``test_retrieval_baseline.py`` which is separately gated.

Skip guard: BGE-M3 weights (≈2GB) must be cached locally. The test skips
with a tracked ID ``SS-SKIP-1`` — un-skip condition: CI preloads the
weights via ``scripts/bootstrap_bge_m3.py`` (Sprint J FU carry →
Sprint S S145 weekly MRR matrix step).
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aiflow.services.rag_engine.service import (
    CollectionInfo,
    RAGEngineService,
    _QueryEmbedderAdapter,
)

pytestmark = pytest.mark.integration

_BGE_CACHE = os.getenv("AIFLOW_BGE_M3__CACHE_FOLDER", ".cache/models/bge-m3")


def _bge_m3_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return Path(_BGE_CACHE).exists()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _bge_m3_available(),
    reason="SS-SKIP-1: BGE-M3 weights or sentence-transformers missing — "
    "run scripts/bootstrap_bge_m3.py. Unskip when CI preloads weights "
    "(Sprint J FU carry → Sprint S S145 weekly matrix).",
)
async def test_query_path_resolves_bge_m3_and_produces_1024_dim_vector() -> None:
    """Resolver + adapter + real BGE-M3 = 1024-dim query vector."""
    os.environ.setdefault("AIFLOW_BGE_M3__CACHE_FOLDER", _BGE_CACHE)

    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = MagicMock(name="legacy_fallback_should_not_be_used")

    coll = CollectionInfo(
        id="s143-test",
        name="s143-query-1024",
        embedding_dim=1024,
        embedder_profile_id="bge_m3",
        tenant_id="default",
    )

    resolved = svc._resolve_query_embedder(coll)

    assert isinstance(resolved, _QueryEmbedderAdapter), (
        "expected ProviderRegistry adapter, got "
        f"{type(resolved).__name__} — resolver regressed to fallback"
    )
    assert resolved.embedding_dim == 1024

    vec = await resolved.embed_query("Mi a szerzodes targya?")
    assert isinstance(vec, list)
    assert len(vec) == 1024, f"BGE-M3 Profile A must produce 1024-dim vectors, got {len(vec)}"
    assert all(isinstance(x, float) for x in vec[:8])


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _bge_m3_available(),
    reason="SS-SKIP-1: BGE-M3 weights or sentence-transformers missing — "
    "run scripts/bootstrap_bge_m3.py.",
)
async def test_pgvector_retrieves_1024_dim_chunk_via_resolver_adapter() -> None:
    """Seed a 1024-dim chunk, call search with the resolver's query
    vector, assert the chunk comes back. Proves the flex-dim column
    (Alembic 042) + the S143 resolver + the adapter together make
    1024-dim collections queryable end-to-end."""
    os.environ.setdefault("AIFLOW_BGE_M3__CACHE_FOLDER", _BGE_CACHE)

    from aiflow.vectorstore.pgvector_store import PgVectorStore

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    store = PgVectorStore(database_url=db_url, table_name="rag_chunks")
    if store.mode != "postgresql":
        pytest.skip("SS-SKIP-1-DB: pgvector store not in postgresql mode")

    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = MagicMock(name="legacy_fallback")

    coll_name = f"s143_query_{uuid.uuid4().hex[:8]}"
    coll = CollectionInfo(
        id="s143-pg-test",
        name=coll_name,
        embedding_dim=1024,
        embedder_profile_id="bge_m3",
        tenant_id="default",
    )

    resolved = svc._resolve_query_embedder(coll)

    chunk_texts = [
        "A szerzodes targya az informatikai rendszerfejlesztes.",
        "A szolgaltato kotelessege a hibamentes uzemeltetes biztositasa.",
        "A dij havi osszege 1.5 millio forint, amely magaban foglalja a tamogatast.",
    ]
    vectors = [await resolved.embed_query(t) for t in chunk_texts]
    assert all(len(v) == 1024 for v in vectors)

    chunk_ids = [str(uuid.uuid4()) for _ in chunk_texts]
    chunks = [
        {
            "id": chunk_ids[i],
            "chunk_id": chunk_ids[i],
            "content": t,
            "metadata": {"lang": "hu"},
            "document_name": "s143-doc",
            "chunk_index": i,
        }
        for i, t in enumerate(chunk_texts)
    ]

    try:
        await store.upsert_chunks(
            collection=coll_name,
            skill_name="rag_engine",
            chunks=chunks,
            embeddings=vectors,
        )

        q_vec = await resolved.embed_query("Mi a szerzodes targya?")
        assert len(q_vec) == 1024

        results = await store.search(
            collection=coll_name,
            skill_name="rag_engine",
            query_embedding=q_vec,
            query_text="Mi a szerzodes targya?",
            top_k=3,
            search_mode="vector",
        )

        assert len(results) > 0, (
            "pgvector flex-dim search returned 0 hits for a 1024-dim "
            "query vector — migration 042 flex-dim + S143 adapter path "
            "is broken."
        )
        top_contents = [r.content for r in results]
        assert any("szerzodes targya" in c for c in top_contents), (
            f"top-3 did not contain the expected chunk. Got: {top_contents}"
        )
    finally:
        backend = store._backend  # noqa: SLF001 — test-only cleanup
        pool = await backend._ensure_pool()  # noqa: SLF001
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM rag_chunks WHERE collection = $1", coll_name)
