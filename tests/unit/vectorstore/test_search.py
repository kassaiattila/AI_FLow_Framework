"""
@test_registry:
    suite: vectorstore-unit
    component: vectorstore.search
    covers: [src/aiflow/vectorstore/search.py]
    phase: 2
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [vectorstore, search, hybrid, rrf]
"""
import uuid
from unittest.mock import AsyncMock

import pytest

from aiflow.vectorstore.base import SearchResult
from aiflow.vectorstore.search import HybridSearchEngine


def _make_result(score: float, vs: float = 0, ks: float = 0) -> SearchResult:
    return SearchResult(chunk_id=uuid.uuid4(), content=f"chunk_{score}",
                        score=score, vector_score=vs, keyword_score=ks)

class TestHybridSearchEngine:
    @pytest.fixture
    def mock_store(self):
        store = AsyncMock()
        store.search.return_value = [
            _make_result(0.9, vs=0.9, ks=0.3),
            _make_result(0.7, vs=0.5, ks=0.8),
            _make_result(0.8, vs=0.7, ks=0.6),
        ]
        return store

    @pytest.fixture
    def engine(self, mock_store):
        return HybridSearchEngine(mock_store, vector_weight=0.6, keyword_weight=0.4)

    @pytest.mark.asyncio
    async def test_search_returns_results(self, engine):
        results = await engine.search("coll", "skill", [0.1, 0.2], "hello", top_k=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_vector_only_without_text(self, engine, mock_store):
        mock_store.search.return_value = [_make_result(0.9, vs=0.9)]
        results = await engine.search("coll", "skill", [0.1], top_k=5)
        assert len(results) == 1

    def test_weights(self, engine):
        assert engine.vector_weight == 0.6
        assert engine.keyword_weight == 0.4

    @pytest.mark.asyncio
    async def test_rrf_reranking(self, engine):
        results = await engine.search("coll", "skill", [0.1], "text", top_k=10)
        assert len(results) > 0
        # RRF scores should be positive
        for r in results:
            assert r.score > 0
