"""UnstructuredChunker — token-aware chunker over ParserResult text.

Introduced by S101 (Sprint J / UC2 RAG session 2). Takes the plain-text
output of a ParserProvider (fast path: :class:`UnstructuredParser`,
standard path: :class:`DoclingStandardParser`) and emits ChunkResult
batches sized to fit embedder context windows.

Chunking strategy: fixed token window (``chunk_size_tokens`` = 512) with
sliding overlap (``overlap_tokens`` = 50) measured in ``tiktoken``
``cl100k_base`` tokens. When ``tiktoken`` is unavailable we fall back to
a character-length heuristic so unit tests can still exercise the
chunker without heavy runtime deps.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md §11,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint J.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from aiflow.contracts.chunk_result import ChunkResult
from aiflow.providers.interfaces import ChunkerProvider
from aiflow.providers.metadata import ProviderMetadata

if TYPE_CHECKING:
    from aiflow.contracts.parser_result import ParserResult
    from aiflow.intake.package import IntakePackage

__all__ = [
    "UnstructuredChunker",
    "UnstructuredChunkerConfig",
]

logger = structlog.get_logger(__name__)

_TIKTOKEN_ENCODING = "cl100k_base"
_CHAR_PER_TOKEN_FALLBACK = 4  # ~4 chars per token on average for Latin text


class UnstructuredChunkerConfig(BaseModel):
    """Config for :class:`UnstructuredChunker`."""

    model_config = ConfigDict(extra="forbid")

    chunk_size_tokens: int = Field(default=512, gt=0, le=8192)
    overlap_tokens: int = Field(default=50, ge=0)
    tokenizer_encoding: str = Field(default=_TIKTOKEN_ENCODING, min_length=1)


class UnstructuredChunker(ChunkerProvider):
    """Token-windowed chunker over :class:`ParserResult` text."""

    PROVIDER_NAME = "unstructured"

    def __init__(self, config: UnstructuredChunkerConfig | None = None) -> None:
        self._config = config or UnstructuredChunkerConfig()
        if self._config.overlap_tokens >= self._config.chunk_size_tokens:
            raise ValueError(
                "overlap_tokens must be smaller than chunk_size_tokens "
                f"(got overlap={self._config.overlap_tokens}, "
                f"size={self._config.chunk_size_tokens})"
            )
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="0.1.0",
            supported_types=["text"],
            speed_class="fast",
            gpu_required=False,
            cost_class="free",
            license="Apache-2.0",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    async def chunk(
        self,
        parser_result: ParserResult,
        package_context: IntakePackage,
    ) -> list[ChunkResult]:
        text = (parser_result.text or parser_result.markdown or "").strip()
        if not text:
            logger.info(
                "unstructured_chunker_empty_text",
                file_id=str(parser_result.file_id),
                parser_name=parser_result.parser_name,
            )
            return []

        chunks = await asyncio.to_thread(self._chunk_text_sync, text)
        results: list[ChunkResult] = []
        for idx, (chunk_text, token_count) in enumerate(chunks):
            if not chunk_text.strip():
                continue
            results.append(
                ChunkResult(
                    source_file_id=parser_result.file_id,
                    package_id=package_context.package_id,
                    tenant_id=package_context.tenant_id,
                    text=chunk_text,
                    token_count=token_count,
                    chunk_index=idx,
                    metadata={
                        "chunker_name": self.PROVIDER_NAME,
                        "chunk_size_tokens": self._config.chunk_size_tokens,
                        "overlap_tokens": self._config.overlap_tokens,
                        "parser_name": parser_result.parser_name,
                    },
                )
            )

        logger.info(
            "unstructured_chunker_done",
            file_id=str(parser_result.file_id),
            package_id=str(package_context.package_id),
            chunks=len(results),
            source_chars=len(text),
        )
        return results

    def _chunk_text_sync(self, text: str) -> list[tuple[str, int]]:
        """Return ``(chunk_text, token_count)`` tuples."""
        encoder = self._load_encoder()
        if encoder is None:
            return self._chunk_by_chars(text)
        return self._chunk_by_tokens(text, encoder)

    def _chunk_by_tokens(
        self,
        text: str,
        encoder: Any,
    ) -> list[tuple[str, int]]:
        tokens = encoder.encode(text)
        size = self._config.chunk_size_tokens
        overlap = self._config.overlap_tokens
        step = max(1, size - overlap)

        chunks: list[tuple[str, int]] = []
        for start in range(0, len(tokens), step):
            window = tokens[start : start + size]
            if not window:
                break
            decoded = encoder.decode(window)
            chunks.append((decoded, len(window)))
            if start + size >= len(tokens):
                break
        return chunks

    def _chunk_by_chars(self, text: str) -> list[tuple[str, int]]:
        """Byte-length fallback used when tiktoken is not installed."""
        size_chars = self._config.chunk_size_tokens * _CHAR_PER_TOKEN_FALLBACK
        overlap_chars = self._config.overlap_tokens * _CHAR_PER_TOKEN_FALLBACK
        step = max(1, size_chars - overlap_chars)

        chunks: list[tuple[str, int]] = []
        for start in range(0, len(text), step):
            window = text[start : start + size_chars]
            if not window:
                break
            approx_tokens = max(1, len(window) // _CHAR_PER_TOKEN_FALLBACK)
            chunks.append((window, approx_tokens))
            if start + size_chars >= len(text):
                break
        return chunks

    def _load_encoder(self) -> Any | None:
        try:
            import tiktoken
        except ImportError:
            logger.warning("unstructured_chunker_tiktoken_missing")
            return None
        try:
            return tiktoken.get_encoding(self._config.tokenizer_encoding)
        except Exception as exc:
            logger.warning(
                "unstructured_chunker_encoding_load_failed",
                encoding=self._config.tokenizer_encoding,
                error=str(exc),
            )
            return None

    async def health_check(self) -> bool:
        try:
            encoder = await asyncio.to_thread(self._load_encoder)
            if encoder is None:
                return True  # fallback path is operational
            return bool(encoder.encode("ping"))
        except Exception as exc:
            logger.warning("unstructured_chunker_health_check_failed", error=str(exc))
            return False
