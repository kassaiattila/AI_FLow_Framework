"""UC2 RAG retrieval baseline — MRR@5 on real pgvector for both profiles.

@test_registry
suite: integration_services_rag_engine
tags: [integration, services, rag_engine, sprint_j, retrieval, real, live]

Sprint J / UC2 (v1.4.6 / S103) — gates UC2 ``done``.

Loads ``tests/fixtures/rag/baseline_2026_04_25.json`` (bilingual hu/en corpus
+ gold question/chunk pairs), ingests the chunks into a freshly-created
``rag_chunks`` collection with a flex-dim embedding column, then queries the
pgvector backend and computes ``MRR@5`` per language and aggregated.

Two profiles:

* **Profile A** — :class:`BGEM3Embedder` (local, 1024-dim). Requires
  ``sentence_transformers`` + the BAAI/bge-m3 weights on disk. Skip if
  ``SentenceTransformer`` refuses to load.

* **Profile B** — :class:`OpenAIEmbedder` (cloud, 1536-dim) against the
  public OpenAI embeddings API. Skip unless ``OPENAI_API_KEY`` is present
  in the process env (loaded from ``.env`` at import time) and the env
  gate ``AIFLOW_RUN_LIVE_RAG_BASELINE=1`` is set so the test does not
  burn real API credits in every CI run.

Acceptance: each active profile must reach ``MRR@5 >= 0.55`` on the full
question set. ``MRR@5 < 0.40`` is a HARD STOP per the S103 plan — a very
weak baseline points to a real provider regression, not noise.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from aiflow.providers.embedder import BGEM3Embedder, OpenAIEmbedder
from aiflow.vectorstore.pgvector_store import PgVectorStore

_TESTS_DIR = Path(__file__).resolve().parents[3]
FIXTURE_PATH = _TESTS_DIR / "fixtures" / "rag" / "baseline_2026_04_25.json"

_PROJECT_ROOT = _TESTS_DIR.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)

_LIVE_GATE = os.getenv("AIFLOW_RUN_LIVE_RAG_BASELINE", "")
_BGE_CACHE = os.getenv("AIFLOW_BGE_M3__CACHE_FOLDER", ".cache/models/bge-m3")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture() -> dict:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _mrr_at_k(ranked: list[str], expected: list[str], k: int = 5) -> float:
    for position, chunk_id in enumerate(ranked[:k], start=1):
        if chunk_id in expected:
            return 1.0 / position
    return 0.0


async def _ingest_fixture(
    store: PgVectorStore,
    collection: str,
    embedder,
    chunks: list[dict],
) -> None:
    texts = [c["text"] for c in chunks]
    vectors = await embedder.embed(texts)
    chunk_dicts = [
        {
            "id": c["id"],
            "chunk_id": c["id"],
            "content": c["text"],
            "metadata": {"lang": c["lang"]},
            "document_name": c["id"],
            "chunk_index": i,
        }
        for i, c in enumerate(chunks)
    ]
    await store.upsert_chunks(
        collection=collection,
        skill_name="rag_baseline",
        chunks=chunk_dicts,
        embeddings=vectors,
    )


async def _run_baseline(embedder) -> dict[str, float]:
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    store = PgVectorStore(database_url=db_url, table_name="rag_chunks")
    assert store.mode == "postgresql", "baseline requires real pgvector"

    fixture = _load_fixture()
    unique = f"rag_baseline_{uuid.uuid4().hex[:8]}"

    try:
        await _ingest_fixture(store, unique, embedder, fixture["chunks"])

        scores_hu: list[float] = []
        scores_en: list[float] = []
        for q in fixture["questions"]:
            q_vec = (await embedder.embed([q["question"]]))[0]
            results = await store.search(
                collection=unique,
                skill_name="rag_baseline",
                query_embedding=q_vec,
                query_text=q["question"],
                top_k=5,
                search_mode="vector",
            )
            ranked_ids = [str(r.chunk_id) for r in results]
            score = _mrr_at_k(ranked_ids, q["expected"], k=5)
            (scores_hu if q["lang"] == "hu" else scores_en).append(score)

        total = scores_hu + scores_en
        return {
            "mrr@5": sum(total) / len(total) if total else 0.0,
            "mrr@5_hu": sum(scores_hu) / len(scores_hu) if scores_hu else 0.0,
            "mrr@5_en": sum(scores_en) / len(scores_en) if scores_en else 0.0,
        }
    finally:
        await _cleanup(store, unique)


async def _cleanup(store: PgVectorStore, collection: str) -> None:
    # PgVectorStore has no public DELETE-by-collection, so reach into the pool.
    backend = store._backend  # noqa: SLF001 — test-only cleanup path
    pool = await backend._ensure_pool()  # noqa: SLF001
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rag_chunks WHERE collection = $1", collection)


# ---------------------------------------------------------------------------
# Profile A — BGE-M3 (local, free)
# ---------------------------------------------------------------------------


def _bge_m3_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return Path(_BGE_CACHE).exists()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _bge_m3_available(),
    reason="BGE-M3 weights or sentence-transformers missing — run scripts/bootstrap_bge_m3.py",
)
async def test_retrieval_baseline_profile_a_bge_m3() -> None:
    os.environ.setdefault("AIFLOW_BGE_M3__CACHE_FOLDER", _BGE_CACHE)
    embedder = BGEM3Embedder()

    scores = await _run_baseline(embedder)

    assert scores["mrr@5"] >= 0.40, (
        f"Profile A MRR@5 {scores['mrr@5']:.3f} < 0.40 hard floor — "
        f"points to a BGE-M3 regression. Full scores: {scores}"
    )
    assert scores["mrr@5"] >= 0.55, (
        f"Profile A MRR@5 {scores['mrr@5']:.3f} < 0.55 baseline target. Full scores: {scores}"
    )


# ---------------------------------------------------------------------------
# Profile B — OpenAI (cloud, paid, gated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or _LIVE_GATE != "1",
    reason="Profile B requires OPENAI_API_KEY and AIFLOW_RUN_LIVE_RAG_BASELINE=1",
)
async def test_retrieval_baseline_profile_b_openai() -> None:
    embedder = OpenAIEmbedder()

    scores = await _run_baseline(embedder)

    assert scores["mrr@5"] >= 0.40, (
        f"Profile B MRR@5 {scores['mrr@5']:.3f} < 0.40 hard floor. Full: {scores}"
    )
    assert scores["mrr@5"] >= 0.55, (
        f"Profile B MRR@5 {scores['mrr@5']:.3f} < 0.55 baseline target. Full: {scores}"
    )
