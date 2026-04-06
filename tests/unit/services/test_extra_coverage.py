"""
@test_registry:
    suite: service-unit
    component: services.extra_coverage
    covers:
        - src/aiflow/services/advanced_chunker/service.py
        - src/aiflow/services/data_router/service.py
        - src/aiflow/services/reranker/service.py
    phase: B2.2
    priority: medium
    estimated_duration_ms: 500
    requires_services: []
    tags: [service, edge-case, coverage, chunker, router, reranker]
"""

from __future__ import annotations

import pytest

from aiflow.services.advanced_chunker.service import (
    AdvancedChunkerConfig,
    AdvancedChunkerService,
    ChunkConfig,
    ChunkStrategy,
)
from aiflow.services.data_router.service import (
    DataRouterConfig,
    DataRouterService,
    RoutingRule,
)
from aiflow.services.reranker.service import (
    RerankConfig,
    RerankerConfig,
    RerankerService,
)


class TestExtraCoverage:
    @pytest.mark.asyncio
    async def test_chunker_recursive_strategy(self) -> None:
        """recursive strategy splits by separators (paragraph → sentence → word)."""
        svc = AdvancedChunkerService(config=AdvancedChunkerConfig())
        text = (
            "First paragraph content here.\n\n"
            "Second paragraph has more text. It has multiple sentences.\n\n"
            "Third paragraph is short."
        )
        config = ChunkConfig(strategy=ChunkStrategy.RECURSIVE, chunk_size=60, chunk_overlap=0)
        result = await svc.chunk(text, config)
        assert result.strategy_used == "recursive"
        assert result.total_chunks >= 2

    @pytest.mark.asyncio
    async def test_chunker_parent_child_strategy(self) -> None:
        """parent_child strategy creates hierarchical child chunks."""
        svc = AdvancedChunkerService(config=AdvancedChunkerConfig())
        text = "A" * 500
        config = ChunkConfig(
            strategy=ChunkStrategy.PARENT_CHILD,
            parent_chunk_size=200,
            child_chunk_size=50,
            chunk_overlap=0,
        )
        result = await svc.chunk(text, config)
        assert result.strategy_used == "parent_child"
        assert result.total_chunks >= 5

    @pytest.mark.asyncio
    async def test_router_unknown_action(self) -> None:
        """route_files with unknown action returns error in RoutedFile."""
        svc = DataRouterService(config=DataRouterConfig())
        files = [{"file_path": "/tmp/test.pdf", "status": "ready"}]
        rules = [
            RoutingRule(
                condition="status == 'ready'",
                action="unknown_action",
                config={},
            ),
        ]
        results = await svc.route_files(files, rules)
        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown action" in (results[0].error or "")

    @pytest.mark.asyncio
    async def test_router_no_rule_match(self) -> None:
        """route_files returns action='none' when no rule matches."""
        svc = DataRouterService(config=DataRouterConfig())
        files = [{"file_path": "/tmp/test.pdf", "status": "pending"}]
        rules = [
            RoutingRule(
                condition="status == 'completed'",
                action="tag",
                config={},
            ),
        ]
        results = await svc.route_files(files, rules)
        assert len(results) == 1
        assert results[0].action == "none"
        assert results[0].rule_matched is None
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_reranker_score_threshold_filter(self) -> None:
        """rerank with score_threshold filters low-score results."""
        svc = RerankerService(config=RerankerConfig(default_model="flashrank"))
        candidates = [{"content": f"Document {i}", "chunk_id": f"c{i}"} for i in range(5)]
        # Flashrank fallback gives 1/1, 1/2, 1/3, 1/4, 1/5
        # score_threshold=0.4 should filter out 1/3=0.33, 1/4=0.25, 1/5=0.2
        config = RerankConfig(model="flashrank", score_threshold=0.4, return_top=10)
        results = await svc.rerank("test", candidates, config=config)
        assert all(r.score >= 0.4 for r in results)
        assert len(results) < 5
