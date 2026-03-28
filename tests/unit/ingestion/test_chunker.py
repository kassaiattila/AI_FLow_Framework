"""
@test_registry:
    suite: core-unit extended
    component: ingestion.chunkers
    covers: [src/aiflow/ingestion/chunkers/semantic_chunker.py]
    phase: 3
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [ingestion, chunker, semantic]
"""
import pytest

from aiflow.ingestion.chunkers.semantic_chunker import (
    Chunk,
    ChunkingConfig,
    ChunkingStrategy,
    SemanticChunker,
)


class TestChunkingConfig:
    def test_defaults(self):
        cfg = ChunkingConfig()
        assert cfg.strategy == ChunkingStrategy.SEMANTIC
        assert cfg.target_chunk_tokens == 512
        assert cfg.max_chunk_tokens == 1024
        assert cfg.overlap_tokens == 64
        assert cfg.min_chunk_tokens == 32

    def test_custom(self):
        cfg = ChunkingConfig(
            strategy=ChunkingStrategy.FIXED,
            target_chunk_tokens=256,
            max_chunk_tokens=512,
            overlap_tokens=32,
            min_chunk_tokens=16,
        )
        assert cfg.strategy == ChunkingStrategy.FIXED
        assert cfg.target_chunk_tokens == 256


class TestSemanticChunker:
    def test_empty_text(self):
        chunker = SemanticChunker()
        result = chunker.chunk("")
        assert result == []

    def test_short_text_single_chunk(self):
        chunker = SemanticChunker()
        text = "This is a short paragraph with enough words to exceed the minimum."
        cfg = ChunkingConfig(min_chunk_tokens=1)
        result = chunker.chunk(text, cfg)
        assert len(result) == 1
        assert result[0].chunk_index == 0
        assert result[0].content == text

    def test_splits_on_headings(self):
        chunker = SemanticChunker()
        text = (
            "Introduction paragraph with enough text to pass the minimum token threshold.\n\n"
            "## Section One\n\n"
            "Content of section one with sufficient length to be a valid chunk on its own.\n\n"
            "## Section Two\n\n"
            "Content of section two also long enough to be kept as a separate chunk."
        )
        cfg = ChunkingConfig(
            target_chunk_tokens=30,
            max_chunk_tokens=200,
            overlap_tokens=0,
            min_chunk_tokens=5,
        )
        result = chunker.chunk(text, cfg)
        assert len(result) >= 2

    def test_overlap_applied(self):
        chunker = SemanticChunker()
        text = (
            "First section has some meaningful content here.\n\n"
            "Second section follows with different content."
        )
        cfg = ChunkingConfig(
            target_chunk_tokens=10,
            max_chunk_tokens=100,
            overlap_tokens=5,
            min_chunk_tokens=1,
        )
        result = chunker.chunk(text, cfg)
        # With overlap, second chunk should contain tail of first
        if len(result) >= 2:
            # The second chunk should start with overlap from the first
            assert len(result[1].content) > len("Second section follows with different content.")

    def test_min_chunk_filtering(self):
        chunker = SemanticChunker()
        text = "Hi\n\nThis is a substantially longer paragraph that should survive filtering."
        cfg = ChunkingConfig(
            target_chunk_tokens=200,
            max_chunk_tokens=400,
            overlap_tokens=0,
            min_chunk_tokens=10,
        )
        result = chunker.chunk(text, cfg)
        for chunk in result:
            assert chunk.token_count >= 10

    def test_chunk_indices_sequential(self):
        chunker = SemanticChunker()
        text = (
            "Paragraph one with enough text.\n\n"
            "Paragraph two with enough text.\n\n"
            "Paragraph three with enough text."
        )
        cfg = ChunkingConfig(
            target_chunk_tokens=10,
            max_chunk_tokens=50,
            overlap_tokens=0,
            min_chunk_tokens=1,
        )
        result = chunker.chunk(text, cfg)
        for i, chunk in enumerate(result):
            assert chunk.chunk_index == i
