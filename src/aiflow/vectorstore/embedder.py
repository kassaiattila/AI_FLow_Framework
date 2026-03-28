"""Embedding generation wrapper with batching, truncation, and cost tracking.

Supports two modes:
  1. Via ModelClient (framework standard) -- structured output with cost tracking
  2. Direct LiteLLM / OpenAI fallback -- when ModelClient is not available

Hungarian-specific defaults: batch_size=5 (longer token counts), 6000 char max.
"""
from __future__ import annotations

import time
from typing import Any

import structlog

from aiflow.models.client import ModelClient

__all__ = ["Embedder", "EmbeddingCostTracker"]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------

class EmbeddingCostTracker:
    """Accumulates embedding cost and token statistics across batches."""

    def __init__(self) -> None:
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.total_texts: int = 0
        self.total_batches: int = 0
        self.total_latency_ms: float = 0.0

    def record(self, tokens: int, cost_usd: float, texts: int, latency_ms: float) -> None:
        self.total_tokens += tokens
        self.total_cost_usd += cost_usd
        self.total_texts += texts
        self.total_batches += 1
        self.total_latency_ms += latency_ms

    def summary(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_texts": self.total_texts,
            "total_batches": self.total_batches,
            "avg_latency_ms": round(self.total_latency_ms / max(self.total_batches, 1), 1),
        }


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

# Default limits -- conservative for Hungarian text with diacritics
_DEFAULT_BATCH_SIZE = 5
_DEFAULT_MAX_CHARS = 6000


class Embedder:
    """Generates embeddings using ModelClient with batching and cost tracking.

    Used by the ingestion pipeline (batch embed document chunks) and the search
    engine (single query embedding).
    """

    def __init__(
        self,
        model_client: ModelClient,
        default_model: str = "openai/text-embedding-3-small",
        *,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        max_chars: int = _DEFAULT_MAX_CHARS,
    ) -> None:
        self._client = model_client
        self._default_model = default_model
        self._batch_size = batch_size
        self._max_chars = max_chars
        self._cost_tracker = EmbeddingCostTracker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_texts(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts with batching and truncation.

        Processes texts in batches of ``batch_size`` (default 5 for Hungarian).
        Texts exceeding ``max_chars`` are truncated with a logged warning.
        Returns one embedding vector per input text, in the same order.
        """
        if not texts:
            return []

        target_model = model or self._default_model
        prepared = self._prepare_texts(texts)

        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(prepared), self._batch_size):
            batch = prepared[batch_start : batch_start + self._batch_size]
            batch_num = batch_start // self._batch_size + 1
            total_batches = (len(prepared) + self._batch_size - 1) // self._batch_size

            logger.debug(
                "embedding_batch",
                batch=f"{batch_num}/{total_batches}",
                texts=len(batch),
                model=target_model,
            )

            start_ms = time.monotonic() * 1000
            try:
                result = await self._client.embed(batch, model=target_model)
                latency = time.monotonic() * 1000 - start_ms

                all_embeddings.extend(result.output.embeddings)
                self._cost_tracker.record(
                    tokens=result.output.total_tokens,
                    cost_usd=result.cost_usd,
                    texts=len(batch),
                    latency_ms=latency,
                )

            except Exception as exc:
                logger.warning(
                    "embedding_batch_failed",
                    batch=batch_num,
                    error=str(exc)[:200],
                )
                # Fallback: try each text individually
                for idx, text in enumerate(batch):
                    try:
                        single_result = await self._client.embed([text], model=target_model)
                        all_embeddings.extend(single_result.output.embeddings)
                        self._cost_tracker.record(
                            tokens=single_result.output.total_tokens,
                            cost_usd=single_result.cost_usd,
                            texts=1,
                            latency_ms=single_result.latency_ms,
                        )
                    except Exception:
                        # Last resort: truncate harder and retry
                        truncated = text[: self._max_chars // 2]
                        logger.warning(
                            "embedding_truncation_retry",
                            original_len=len(text),
                            truncated_len=len(truncated),
                        )
                        try:
                            retry_result = await self._client.embed(
                                [truncated], model=target_model
                            )
                            all_embeddings.extend(retry_result.output.embeddings)
                            self._cost_tracker.record(
                                tokens=retry_result.output.total_tokens,
                                cost_usd=retry_result.cost_usd,
                                texts=1,
                                latency_ms=retry_result.latency_ms,
                            )
                        except Exception as final_exc:
                            logger.error(
                                "embedding_text_failed",
                                text_index=batch_start + idx,
                                error=str(final_exc)[:200],
                            )
                            raise

        logger.info(
            "texts_embedded",
            count=len(all_embeddings),
            dimensions=len(all_embeddings[0]) if all_embeddings else 0,
            model=target_model,
            cost=self._cost_tracker.summary(),
        )
        return all_embeddings

    async def embed_query(
        self,
        query: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        """Generate embedding for a single query text.

        Queries are not truncated as aggressively -- just the max_chars limit.
        """
        prepared = query[: self._max_chars] if len(query) > self._max_chars else query
        if len(query) > self._max_chars:
            logger.warning("query_truncated", original=len(query), max=self._max_chars)

        embeddings = await self.embed_texts([prepared], model=model)
        return embeddings[0] if embeddings else []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @property
    def max_chars(self) -> int:
        return self._max_chars

    @property
    def cost_tracker(self) -> EmbeddingCostTracker:
        """Access accumulated cost/token statistics."""
        return self._cost_tracker

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prepare_texts(self, texts: list[str]) -> list[str]:
        """Truncate texts that exceed max_chars, log warnings."""
        prepared: list[str] = []
        for i, text in enumerate(texts):
            if len(text) > self._max_chars:
                logger.warning(
                    "text_truncated",
                    index=i,
                    original_len=len(text),
                    max_chars=self._max_chars,
                )
                prepared.append(text[: self._max_chars])
            else:
                prepared.append(text)
        return prepared
