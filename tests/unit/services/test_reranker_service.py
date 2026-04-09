"""
@test_registry:
    suite: service-unit
    component: services.reranker
    covers: [src/aiflow/services/reranker/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, reranker, rag, scoring, fallback]
"""

from __future__ import annotations

import pytest

from aiflow.services.reranker.service import (
    RerankConfig,
    RerankerConfig,
    RerankerService,
)


@pytest.fixture()
def svc() -> RerankerService:
    # Use flashrank as default so it falls back (flashrank not installed)
    return RerankerService(config=RerankerConfig(default_model="flashrank"))


class TestRerankerService:
    @pytest.mark.asyncio
    async def test_rerank_keyword_strategy(self, svc: RerankerService) -> None:
        """rerank with fallback (no model installed) returns scored results."""
        candidates = [
            {"content": "Python programming guide", "chunk_id": "c1"},
            {"content": "Java enterprise patterns", "chunk_id": "c2"},
            {"content": "Python data science tutorial", "chunk_id": "c3"},
        ]
        # Uses default model which triggers ImportError → fallback
        results = await svc.rerank("Python tutorial", candidates)
        assert len(results) > 0
        # Fallback assigns decaying scores: 1.0, 0.5, 0.33...
        assert all(r.score > 0 for r in results)
        assert results[0].original_rank == 1

    @pytest.mark.asyncio
    async def test_rerank_empty_candidates(self, svc: RerankerService) -> None:
        """rerank with empty candidate list returns empty list."""
        results = await svc.rerank("test query", [])
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_top_k_limit(self, svc: RerankerService) -> None:
        """rerank respects return_top limit."""
        candidates = [{"content": f"Document {i}", "chunk_id": f"c{i}"} for i in range(10)]
        config = RerankConfig(model="flashrank", return_top=2)
        results = await svc.rerank("test", candidates, config=config)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_rerank_score_ordering(self, svc: RerankerService) -> None:
        """rerank returns results in descending score order."""
        candidates = [
            {"content": "first", "chunk_id": "c1"},
            {"content": "second", "chunk_id": "c2"},
            {"content": "third", "chunk_id": "c3"},
        ]
        results = await svc.rerank("query", candidates)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_health_check(self, svc: RerankerService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
