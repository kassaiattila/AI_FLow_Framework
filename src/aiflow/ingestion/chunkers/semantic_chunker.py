"""Semantic chunking strategy.

Splits text on section boundaries (Markdown headings, double newlines) and
merges short fragments to reach target token counts, applying overlap between
consecutive chunks.
"""
from __future__ import annotations

import re
from enum import StrEnum

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "ChunkingStrategy",
    "ChunkingConfig",
    "Chunk",
    "SemanticChunker",
]

logger = structlog.get_logger(__name__)

# A very rough token estimator (1 token ~ 4 chars for Latin/mixed text).
_CHARS_PER_TOKEN = 4

# Section-separator pattern used for semantic splitting.
_SECTION_SPLIT_RE = re.compile(r"(?=\n#{2,3}\s)|\n\n+")


class ChunkingStrategy(StrEnum):
    SEMANTIC = "semantic"
    FIXED = "fixed"


class ChunkingConfig(BaseModel):
    """Configuration for the chunking process."""

    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    target_chunk_tokens: int = Field(default=512, gt=0)
    max_chunk_tokens: int = Field(default=1024, gt=0)
    overlap_tokens: int = Field(default=64, ge=0)
    min_chunk_tokens: int = Field(default=32, ge=0)


class Chunk(BaseModel):
    """A single chunk produced by a chunker."""

    content: str
    token_count: int
    chunk_index: int


def _estimate_tokens(text: str) -> int:
    """Rough token count estimation."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


class SemanticChunker:
    """Split text into semantically coherent chunks.

    1. Split on section separators (``## ``, ``### ``, ``\\n\\n``).
    2. Merge adjacent segments until *target_chunk_tokens* is reached.
    3. Hard-break any segment exceeding *max_chunk_tokens*.
    4. Apply *overlap_tokens* between consecutive chunks.
    5. Drop chunks smaller than *min_chunk_tokens*.
    """

    def chunk(self, text: str, config: ChunkingConfig | None = None) -> list[Chunk]:
        """Split *text* according to *config* and return ordered chunks."""
        cfg = config or ChunkingConfig()

        # Step 1: split into raw segments
        raw_segments = _SECTION_SPLIT_RE.split(text)
        raw_segments = [s.strip() for s in raw_segments if s.strip()]

        if not raw_segments:
            return []

        # Step 2 + 3: merge small segments, hard-break large ones
        merged = self._merge_and_break(raw_segments, cfg)

        # Step 4: apply overlap
        chunks_with_overlap = self._apply_overlap(merged, cfg)

        # Step 5: filter by min_chunk_tokens and build Chunk objects
        result: list[Chunk] = []
        idx = 0
        for text_segment in chunks_with_overlap:
            token_count = _estimate_tokens(text_segment)
            if token_count < cfg.min_chunk_tokens:
                continue
            result.append(Chunk(content=text_segment, token_count=token_count, chunk_index=idx))
            idx += 1

        logger.info("chunker.semantic", total_chunks=len(result))
        return result

    # -- internal helpers --------------------------------------------------

    def _merge_and_break(
        self,
        segments: list[str],
        cfg: ChunkingConfig,
    ) -> list[str]:
        """Merge short segments up to *target*; hard-break those above *max*."""
        merged: list[str] = []
        buffer = ""

        for seg in segments:
            candidate = f"{buffer}\n\n{seg}".strip() if buffer else seg
            if _estimate_tokens(candidate) <= cfg.target_chunk_tokens:
                buffer = candidate
            else:
                if buffer:
                    merged.append(buffer)
                # Hard-break oversized segment
                if _estimate_tokens(seg) > cfg.max_chunk_tokens:
                    merged.extend(self._hard_break(seg, cfg.max_chunk_tokens))
                    buffer = ""
                else:
                    buffer = seg

        if buffer:
            merged.append(buffer)

        return merged

    @staticmethod
    def _hard_break(text: str, max_tokens: int) -> list[str]:
        """Force-split *text* into pieces of at most *max_tokens*."""
        max_chars = max_tokens * _CHARS_PER_TOKEN
        pieces: list[str] = []
        while text:
            pieces.append(text[:max_chars].strip())
            text = text[max_chars:].strip()
        return [p for p in pieces if p]

    @staticmethod
    def _apply_overlap(segments: list[str], cfg: ChunkingConfig) -> list[str]:
        """Prepend *overlap_tokens* worth of the previous chunk to each chunk."""
        if cfg.overlap_tokens <= 0 or len(segments) <= 1:
            return segments

        overlap_chars = cfg.overlap_tokens * _CHARS_PER_TOKEN
        result = [segments[0]]
        for i in range(1, len(segments)):
            prev_tail = segments[i - 1][-overlap_chars:]
            result.append(f"{prev_tail}\n\n{segments[i]}".strip())
        return result
