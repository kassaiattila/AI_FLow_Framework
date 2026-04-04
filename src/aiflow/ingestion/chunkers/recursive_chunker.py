"""Recursive text chunker - hierarchical splitting strategy.

Based on the Cubix RAG reference (02_rag_pipeline_es_dokumentum_feldolgozas.md):
The text is split along increasingly fine separators:
1. First try double newline (paragraph boundary)
2. If chunk still too large, try single newline
3. Then sentence boundary (". ")
4. Finally word boundary (" ")

This preserves logical structure better than fixed-size chunking.
Overlap ensures context continuity between chunks.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["RecursiveChunker", "ChunkingConfig", "Chunk"]

logger = structlog.get_logger(__name__)


class ChunkingConfig(BaseModel):
    """Configuration for recursive chunking."""

    strategy: str = "recursive"
    chunk_size: int = 2000  # characters (not tokens; ~500 tokens for Hungarian)
    chunk_overlap: int = 200  # overlap characters
    separators: list[str] = Field(
        default_factory=lambda: ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    )
    min_chunk_size: int = 100  # discard chunks smaller than this


class Chunk(BaseModel):
    """A single chunk of text with metadata."""

    text: str
    index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    char_count: int = 0
    separator_used: str = ""


class RecursiveChunker:
    """Recursively splits text using hierarchical separators.

    Follows the Cubix RAG course recommendation for recursive chunking.
    """

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split text into chunks using recursive separator hierarchy.

        Args:
            text: Full document text to chunk.
            metadata: Base metadata to include in each chunk.

        Returns:
            List of Chunk objects with text, index, and metadata.
        """
        base_meta = metadata or {}
        raw_chunks = self._recursive_split(
            text,
            self.config.separators,
            self.config.chunk_size,
        )

        # Apply overlap
        chunks_with_overlap = self._apply_overlap(raw_chunks)

        # Filter and create Chunk objects
        result: list[Chunk] = []
        for i, (chunk_text, separator) in enumerate(chunks_with_overlap):
            if len(chunk_text.strip()) < self.config.min_chunk_size:
                continue
            result.append(
                Chunk(
                    text=chunk_text.strip(),
                    index=i,
                    metadata={
                        **base_meta,
                        "chunk_index": i,
                        "chunk_strategy": "recursive",
                        "separator_used": repr(separator),
                    },
                    char_count=len(chunk_text.strip()),
                    separator_used=separator,
                )
            )

        logger.info(
            "recursive_chunking_done",
            input_chars=len(text),
            chunks=len(result),
            avg_chunk_size=sum(c.char_count for c in result) // max(len(result), 1),
            config_chunk_size=self.config.chunk_size,
        )
        return result

    def chunk_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> list[Chunk]:
        """Chunk multiple documents, preserving document-level metadata."""
        all_chunks: list[Chunk] = []
        global_index = 0

        for doc in documents:
            text = doc.get("text", doc.get("markdown", ""))
            doc_meta = {
                "source_document": doc.get("name", ""),
                "file_type": doc.get("file_type", ""),
                "language": doc.get("language", "hu"),
            }
            doc_chunks = self.chunk_text(text, metadata=doc_meta)

            for chunk in doc_chunks:
                chunk.index = global_index
                chunk.metadata["chunk_index"] = global_index
                global_index += 1
                all_chunks.append(chunk)

        logger.info(
            "recursive_chunking_batch",
            documents=len(documents),
            total_chunks=len(all_chunks),
        )
        return all_chunks

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
        max_size: int,
    ) -> list[tuple[str, str]]:
        """Recursively split text along separator hierarchy.

        Returns list of (chunk_text, separator_used) tuples.
        """
        if len(text) <= max_size:
            return [(text, "")]

        if not separators:
            # No more separators - force split at max_size
            chunks = []
            for i in range(0, len(text), max_size):
                chunks.append((text[i : i + max_size], "force"))
            return chunks

        separator = separators[0]
        remaining_separators = separators[1:]

        parts = text.split(separator)

        if len(parts) == 1:
            # This separator doesn't split the text - try next
            return self._recursive_split(text, remaining_separators, max_size)

        # Merge parts into chunks that fit max_size
        chunks: list[tuple[str, str]] = []
        current = ""

        for part in parts:
            candidate = current + separator + part if current else part

            if len(candidate) <= max_size:
                current = candidate
            else:
                # Current chunk is full
                if current:
                    chunks.append((current, separator))
                # Check if this part alone is too big
                if len(part) > max_size:
                    # Recursively split with finer separators
                    sub_chunks = self._recursive_split(part, remaining_separators, max_size)
                    chunks.extend(sub_chunks)
                    current = ""
                else:
                    current = part

        if current:
            chunks.append((current, separator))

        return chunks

    def _apply_overlap(
        self,
        chunks: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        """Add overlap from the end of the previous chunk to the start of the next."""
        if not chunks or self.config.chunk_overlap <= 0:
            return chunks

        result = [chunks[0]]
        overlap = self.config.chunk_overlap

        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1][0]
            curr_text = chunks[i][0]
            separator = chunks[i][1]

            # Take last N chars from previous chunk as overlap prefix
            overlap_text = prev_text[-overlap:] if len(prev_text) > overlap else ""

            # Find a clean break point (newline or space)
            clean_start = 0
            for j, ch in enumerate(overlap_text):
                if ch in ("\n", " "):
                    clean_start = j + 1
                    break

            overlap_prefix = overlap_text[clean_start:]
            combined = overlap_prefix + curr_text if overlap_prefix else curr_text

            result.append((combined, separator))

        return result
