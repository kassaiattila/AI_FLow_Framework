"""Advanced chunker service — 6-strategy text chunking for RAG pipelines."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "ChunkStrategy",
    "ChunkConfig",
    "ChunkResult",
    "AdvancedChunkerConfig",
    "AdvancedChunkerService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChunkStrategy(StrEnum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    SENTENCE_WINDOW = "sentence_window"
    DOCUMENT_AWARE = "document_aware"
    PARENT_CHILD = "parent_child"


class ChunkConfig(BaseModel):
    """Configuration for a single chunking operation."""

    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = 512
    chunk_overlap: int = 64
    similarity_threshold: float = 0.75
    window_size: int = 3
    heading_patterns: list[str] = Field(
        default_factory=lambda: [r"^#{1,6}\s", r"^\d+\.\s"]
    )
    parent_chunk_size: int = 2048
    child_chunk_size: int = 256


class ChunkResult(BaseModel):
    """Result of a chunking operation."""

    chunks: list[dict[str, Any]] = Field(default_factory=list)
    strategy_used: str = ""
    total_chunks: int = 0
    avg_chunk_size: float = 0.0


class AdvancedChunkerConfig(ServiceConfig):
    """Service-level configuration."""

    default_strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    max_chunk_size: int = 4096


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AdvancedChunkerService(BaseService):
    """Text chunking service with 6 strategies for RAG pipelines.

    Strategies:
    - fixed: split by character count with overlap
    - recursive: split by separators (paragraphs -> sentences -> words)
    - semantic: split by embedding similarity (stub — needs embedder)
    - sentence_window: sliding window of N sentences
    - document_aware: split by headings / document structure
    - parent_child: hierarchical parent + child chunks
    """

    def __init__(self, config: AdvancedChunkerConfig | None = None) -> None:
        self._ext_config = config or AdvancedChunkerConfig()
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "advanced_chunker"

    @property
    def service_description(self) -> str:
        return "Multi-strategy text chunking for RAG pipelines"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Chunk
    # ------------------------------------------------------------------

    async def chunk(self, text: str, config: ChunkConfig | None = None) -> ChunkResult:
        """Chunk text using the specified strategy.

        Args:
            text: Input text to chunk.
            config: Chunking configuration (strategy, sizes, etc.).

        Returns:
            ChunkResult with list of chunks and metadata.
        """
        if not text:
            return ChunkResult(strategy_used="none", total_chunks=0, avg_chunk_size=0.0)

        cfg = config or ChunkConfig(strategy=self._ext_config.default_strategy)
        strategy = cfg.strategy

        dispatch = {
            ChunkStrategy.FIXED: self._chunk_fixed,
            ChunkStrategy.RECURSIVE: self._chunk_recursive,
            ChunkStrategy.SEMANTIC: self._chunk_semantic,
            ChunkStrategy.SENTENCE_WINDOW: self._chunk_sentence_window,
            ChunkStrategy.DOCUMENT_AWARE: self._chunk_document_aware,
            ChunkStrategy.PARENT_CHILD: self._chunk_parent_child,
        }

        handler = dispatch.get(strategy, self._chunk_fixed)
        raw_chunks = handler(text, cfg)

        chunks = [
            {
                "index": i,
                "text": c,
                "char_count": len(c),
                "strategy": strategy.value,
            }
            for i, c in enumerate(raw_chunks)
            if c.strip()
        ]

        total = len(chunks)
        avg_size = sum(c["char_count"] for c in chunks) / total if total > 0 else 0.0

        self._logger.info(
            "chunk_completed",
            strategy=strategy.value,
            total_chunks=total,
            avg_chunk_size=round(avg_size, 1),
        )

        return ChunkResult(
            chunks=chunks,
            strategy_used=strategy.value,
            total_chunks=total,
            avg_chunk_size=round(avg_size, 1),
        )

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _chunk_fixed(self, text: str, config: ChunkConfig) -> list[str]:
        """Split text into fixed-size chunks with overlap."""
        size = config.chunk_size
        overlap = config.chunk_overlap
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start += size - overlap
            if start >= len(text):
                break
        return chunks

    def _chunk_recursive(self, text: str, config: ChunkConfig) -> list[str]:
        """Recursively split by separators: double-newline -> newline -> sentence -> space."""
        separators = ["\n\n", "\n", ". ", " "]
        return self._recursive_split(text, separators, config.chunk_size, config.chunk_overlap)

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
        chunk_size: int,
        overlap: int,
    ) -> list[str]:
        """Recursively split text using a list of separators."""
        if len(text) <= chunk_size:
            return [text]

        if not separators:
            return self._chunk_fixed(
                text, ChunkConfig(chunk_size=chunk_size, chunk_overlap=overlap)
            )

        sep = separators[0]
        remaining_seps = separators[1:]
        parts = text.split(sep)

        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(part) > chunk_size:
                    chunks.extend(
                        self._recursive_split(part, remaining_seps, chunk_size, overlap)
                    )
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current)

        return chunks

    def _chunk_semantic(self, text: str, config: ChunkConfig) -> list[str]:
        """Semantic chunking — stub that falls back to recursive.

        Full implementation requires an embedding model to compute
        sentence similarity and split at low-similarity boundaries.
        """
        self._logger.info(
            "semantic_chunking_stub",
            note="Falling back to recursive — embedder not integrated",
        )
        return self._chunk_recursive(text, config)

    def _chunk_sentence_window(self, text: str, config: ChunkConfig) -> list[str]:
        """Sliding window of N sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if not sentences:
            return [text]

        window = config.window_size
        chunks: list[str] = []
        for i in range(0, len(sentences), max(1, window - 1)):
            window_sentences = sentences[i : i + window]
            chunk = " ".join(window_sentences)
            if chunk.strip():
                chunks.append(chunk)
            if i + window >= len(sentences):
                break

        return chunks

    def _chunk_document_aware(self, text: str, config: ChunkConfig) -> list[str]:
        """Split by heading patterns (Markdown, numbered sections)."""
        combined_pattern = "|".join(f"({p})" for p in config.heading_patterns)
        sections = re.split(f"(?m)(?={combined_pattern})", text)

        chunks: list[str] = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            if len(section) <= config.chunk_size:
                chunks.append(section)
            else:
                chunks.extend(self._chunk_recursive(section, config))

        return chunks

    def _chunk_parent_child(self, text: str, config: ChunkConfig) -> list[str]:
        """Hierarchical chunking: parent chunks contain child chunks.

        Returns child-sized chunks with parent context prepended as metadata.
        """
        parent_cfg = ChunkConfig(
            chunk_size=config.parent_chunk_size,
            chunk_overlap=0,
        )
        parent_chunks = self._chunk_fixed(text, parent_cfg)

        child_cfg = ChunkConfig(
            chunk_size=config.child_chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

        all_children: list[str] = []
        for parent in parent_chunks:
            children = self._chunk_fixed(parent, child_cfg)
            all_children.extend(children)

        return all_children
