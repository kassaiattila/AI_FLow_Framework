"""UC2 RAG ingest via provider registry — real-services integration.

@test_registry
suite: integration_services_rag_engine
tags: [integration, services, rag_engine, sprint_j, phase_1_5, real]

Exercises ``RAGEngineService.ingest_documents`` with
``use_provider_registry=True`` against real PostgreSQL + Redis. The flow
is Parser(UnstructuredParser) → Chunker(UnstructuredChunker) →
Embedder(injected fake). A fake 1536-dim embedder is injected because:

* Profile A (BGE-M3) requires ``sentence_transformers`` + 500MB model
  download — deferred to S102 per the Sprint J kickoff plan.
* Profile B (Azure OpenAI) requires ``AIFLOW_AZURE_OPENAI__*`` env vars
  which are not set in the default dev environment.

The injected fake returns deterministic 1536-dim vectors so we can
assert:

* ``rag_chunks`` row is written with the chunk text.
* ``rag_chunks.embedding_dim`` is populated by the new flow.
* ``embedding_decisions`` row is written once per ingest call.
* Chunk metadata carries ``chunk_index``, ``tenant_id``, ``package_id``,
  ``source_file_id``.

Skips when the small sample PDF fixture is missing.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aiflow.providers.interfaces import EmbedderProvider
from aiflow.providers.metadata import ProviderMetadata
from aiflow.services.rag_engine.service import RAGEngineConfig, RAGEngineService

RAG_DOCS_DIR = Path(__file__).resolve().parents[4] / "e2e-audit" / "test-data" / "rag-docs"


def _pick_small_pdf() -> Path | None:
    if not RAG_DOCS_DIR.is_dir():
        return None
    candidates = sorted(
        (p for p in RAG_DOCS_DIR.glob("*.pdf") if p.is_file()),
        key=lambda p: p.stat().st_size,
    )
    for c in candidates:
        if c.stat().st_size <= 500_000:  # ≤500KB — keeps parse fast
            return c
    return candidates[0] if candidates else None


SAMPLE_PDF = _pick_small_pdf()


pytestmark = pytest.mark.skipif(
    SAMPLE_PDF is None,
    reason=f"No RAG PDFs found at {RAG_DOCS_DIR}; integration test skipped.",
)


# ---------------------------------------------------------------------------
# Fake embedder (1536-dim, deterministic hash-seeded vectors)
# ---------------------------------------------------------------------------


class _FakeEmbedder(EmbedderProvider):
    PROVIDER_NAME = "fake_1536"

    def __init__(self) -> None:
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="0.0.1",
            supported_types=["text"],
            speed_class="fast",
            gpu_required=False,
            cost_class="free",
            license="MIT",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    @property
    def embedding_dim(self) -> int:
        return 1536

    @property
    def model_name(self) -> str:
        return "fake-1536-test"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for t in texts:
            digest = hashlib.sha256(t.encode("utf-8")).digest()
            # Repeat the 32-byte digest out to 1536 floats in [0, 1).
            seed = [b / 255.0 for b in digest]
            vec = (seed * ((1536 // len(seed)) + 1))[:1536]
            vectors.append(vec)
        return vectors

    async def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_url() -> str:
    return os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )


@pytest.fixture
def session_factory(db_url: str) -> async_sessionmaker:  # type: ignore[type-arg]
    engine = create_async_engine(db_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def service(session_factory):
    cfg = RAGEngineConfig(
        use_provider_registry=True,
        provider_registry_profile="B",
        provider_registry_tenant="tenant_it_test",
    )
    svc = RAGEngineService(session_factory=session_factory, config=cfg)
    await svc._start()
    svc.set_embedder_provider_override(_FakeEmbedder())
    yield svc
    await svc._stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_registry_ingest_end_to_end(
    service: RAGEngineService,
    session_factory,
) -> None:
    """Full Parser→Chunker→Embedder flow + EmbeddingDecision + embedding_dim backfill."""
    assert SAMPLE_PDF is not None
    unique = f"uc2_s101_it_{uuid4().hex[:8]}"

    coll = await service.create_collection(name=unique, language="hu")
    result = await service.ingest_documents(
        collection_id=coll.id,
        file_paths=[SAMPLE_PDF],
        language="hu",
    )

    assert not result.errors, f"ingest errors: {result.errors}"
    assert result.files_processed == 1
    assert result.chunks_created >= 1

    async with session_factory() as s:
        row = await s.execute(
            text(
                "SELECT COUNT(*), MIN(embedding_dim), MAX(embedding_dim) "
                "FROM rag_chunks WHERE collection = :name"
            ),
            {"name": coll.name},
        )
        count, min_dim, max_dim = row.fetchone()
        assert count == result.chunks_created
        assert min_dim == 1536
        assert max_dim == 1536

        dec = await s.execute(
            text(
                "SELECT provider_name, model_name, embedding_dim, profile, tenant_id "
                "FROM embedding_decisions "
                "WHERE tenant_id = :tenant "
                "ORDER BY decision_at DESC LIMIT 1"
            ),
            {"tenant": "tenant_it_test"},
        )
        d = dec.fetchone()
        assert d is not None
        assert d[0] == "fake_1536"
        assert d[1] == "fake-1536-test"
        assert d[2] == 1536
        assert d[3] == "B"
        assert d[4] == "tenant_it_test"

    # Cleanup: delete the test collection so repeat runs stay clean.
    await service.delete_collection(coll.id)


@pytest.mark.asyncio
async def test_provider_registry_persists_chunk_provenance(
    service: RAGEngineService,
    session_factory,
) -> None:
    """Chunk metadata carries package_id / source_file_id / chunk_index."""
    assert SAMPLE_PDF is not None
    unique = f"uc2_s101_it_{uuid4().hex[:8]}"
    coll = await service.create_collection(name=unique, language="hu")

    await service.ingest_documents(
        collection_id=coll.id,
        file_paths=[SAMPLE_PDF],
        language="hu",
    )

    async with session_factory() as s:
        row = await s.execute(
            text(
                "SELECT metadata FROM rag_chunks "
                "WHERE collection = :name ORDER BY chunk_index LIMIT 1"
            ),
            {"name": coll.name},
        )
        md_row = row.fetchone()
        assert md_row is not None
        md = md_row[0]
        assert md.get("tenant_id") == "tenant_it_test"
        assert "package_id" in md
        assert "source_file_id" in md
        assert md.get("chunker_name") == "unstructured"

    await service.delete_collection(coll.id)
