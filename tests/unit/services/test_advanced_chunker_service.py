"""
@test_registry:
    suite: service-unit
    component: services.advanced_chunker
    covers: [src/aiflow/services/advanced_chunker/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, chunker, rag, text-processing]
"""

from __future__ import annotations

import pytest

from aiflow.services.advanced_chunker.service import (
    AdvancedChunkerConfig,
    AdvancedChunkerService,
    ChunkConfig,
    ChunkStrategy,
)


@pytest.fixture()
def svc() -> AdvancedChunkerService:
    return AdvancedChunkerService(config=AdvancedChunkerConfig())


class TestAdvancedChunkerService:
    @pytest.mark.asyncio
    async def test_chunk_fixed_strategy(self, svc: AdvancedChunkerService) -> None:
        """chunk with fixed strategy returns ChunkResult with correct chunks."""
        text = "A" * 100
        config = ChunkConfig(strategy=ChunkStrategy.FIXED, chunk_size=30, chunk_overlap=0)
        result = await svc.chunk(text, config)
        assert result.strategy_used == "fixed"
        assert result.total_chunks >= 3
        # All chunks should have text
        assert all(c["text"] for c in result.chunks)

    @pytest.mark.asyncio
    async def test_chunk_sentence_strategy(self, svc: AdvancedChunkerService) -> None:
        """chunk with sentence_window strategy splits by sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        config = ChunkConfig(strategy=ChunkStrategy.SENTENCE_WINDOW, window_size=2)
        result = await svc.chunk(text, config)
        assert result.strategy_used == "sentence_window"
        assert result.total_chunks >= 1

    @pytest.mark.asyncio
    async def test_chunk_respects_max_size(self, svc: AdvancedChunkerService) -> None:
        """chunk with fixed strategy produces chunks within chunk_size."""
        text = "Word " * 200  # 1000 chars
        config = ChunkConfig(strategy=ChunkStrategy.FIXED, chunk_size=50, chunk_overlap=0)
        result = await svc.chunk(text, config)
        for chunk in result.chunks:
            assert chunk["char_count"] <= 50

    @pytest.mark.asyncio
    async def test_chunk_overlap(self, svc: AdvancedChunkerService) -> None:
        """chunk with overlap produces more chunks than without."""
        text = "A" * 200
        no_overlap = ChunkConfig(strategy=ChunkStrategy.FIXED, chunk_size=50, chunk_overlap=0)
        with_overlap = ChunkConfig(strategy=ChunkStrategy.FIXED, chunk_size=50, chunk_overlap=20)
        result_no = await svc.chunk(text, no_overlap)
        result_yes = await svc.chunk(text, with_overlap)
        assert result_yes.total_chunks >= result_no.total_chunks

    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, svc: AdvancedChunkerService) -> None:
        """chunk with empty text returns empty ChunkResult."""
        result = await svc.chunk("")
        assert result.total_chunks == 0
        assert result.chunks == []
