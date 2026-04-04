"""Reranker service — cross-encoder reranking for RAG search results."""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "RankedResult",
    "RerankConfig",
    "RerankerConfig",
    "RerankerService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RerankConfig(BaseModel):
    """Configuration for a single rerank operation."""

    model: str = "bge-reranker-v2-m3"
    top_k: int = 20
    return_top: int = 5
    score_threshold: float = 0.0
    batch_size: int = 32


class RankedResult(BaseModel):
    """A single reranked search result."""

    original_rank: int
    new_rank: int = 0
    score: float = 0.0
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_id: str = ""


class RerankerConfig(ServiceConfig):
    """Service-level configuration."""

    default_model: str = "bge-reranker-v2-m3"
    fallback_model: str = "flashrank"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RerankerService(BaseService):
    """Cross-encoder reranking to improve RAG result quality.

    Supports three backends:
    - bge-reranker-v2-m3: local cross-encoder (sentence-transformers)
    - flashrank: fast CPU-optimized ONNX reranker
    - cohere: cloud API (premium)
    """

    def __init__(self, config: RerankerConfig | None = None) -> None:
        self._ext_config = config or RerankerConfig()
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "reranker"

    @property
    def service_description(self) -> str:
        return "Cross-encoder reranking for RAG search results"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Rerank
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        config: RerankConfig | None = None,
    ) -> list[RankedResult]:
        """Rerank candidates by relevance to query.

        Args:
            query: Search query text.
            candidates: List of dicts with at least 'content' key.
                Optional keys: 'chunk_id', 'metadata', 'score'.
            config: Reranking config (model, top_k, etc.).

        Returns:
            Sorted list of RankedResult (highest score first).
        """
        if not candidates:
            return []

        cfg = config or RerankConfig(model=self._ext_config.default_model)
        model = cfg.model.lower()

        # Limit candidates to top_k before reranking
        candidates = candidates[: cfg.top_k]

        if "cohere" in model:
            scored = await self._rerank_cohere(query, candidates, cfg)
        elif "flashrank" in model:
            scored = self._rerank_flashrank(query, candidates, cfg)
        else:
            # Default: cross-encoder scoring (bge or any HF model)
            scored = self._rerank_cross_encoder(query, candidates, cfg)

        # Sort by score descending
        scored.sort(key=lambda r: r.score, reverse=True)

        # Apply score threshold
        if cfg.score_threshold > 0:
            scored = [r for r in scored if r.score >= cfg.score_threshold]

        # Assign new ranks and limit
        for i, result in enumerate(scored):
            result.new_rank = i + 1

        result_list = scored[: cfg.return_top]

        self._logger.info(
            "rerank_completed",
            model=model,
            input_count=len(candidates),
            output_count=len(result_list),
        )
        return result_list

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _rerank_cross_encoder(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        config: RerankConfig,
    ) -> list[RankedResult]:
        """Rerank using a local cross-encoder model (e.g., BGE)."""
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(config.model)
            pairs = [(query, c.get("content", "")) for c in candidates]
            scores = model.predict(pairs, batch_size=config.batch_size)

            return [
                RankedResult(
                    original_rank=i + 1,
                    score=float(scores[i]),
                    content=c.get("content", ""),
                    metadata=c.get("metadata", {}),
                    chunk_id=c.get("chunk_id", ""),
                )
                for i, c in enumerate(candidates)
            ]
        except ImportError:
            self._logger.warning("sentence_transformers_not_installed")
            return self._rerank_fallback(candidates)

    def _rerank_flashrank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        config: RerankConfig,
    ) -> list[RankedResult]:
        """Rerank using FlashRank (fast CPU ONNX)."""
        try:
            from flashrank import Ranker, RerankRequest

            ranker = Ranker()
            passages = [
                {"text": c.get("content", ""), "meta": c.get("metadata", {})}
                for c in candidates
            ]
            request = RerankRequest(query=query, passages=passages)
            results = ranker.rerank(request)

            return [
                RankedResult(
                    original_rank=i + 1,
                    score=float(r.get("score", 0)),
                    content=candidates[i].get("content", ""),
                    metadata=candidates[i].get("metadata", {}),
                    chunk_id=candidates[i].get("chunk_id", ""),
                )
                for i, r in enumerate(results)
            ]
        except ImportError:
            self._logger.warning("flashrank_not_installed")
            return self._rerank_fallback(candidates)

    async def _rerank_cohere(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        config: RerankConfig,
    ) -> list[RankedResult]:
        """Rerank using Cohere API (premium cloud)."""
        try:
            import cohere

            client = cohere.AsyncClient()
            docs = [c.get("content", "") for c in candidates]
            response = await client.rerank(
                query=query,
                documents=docs,
                model="rerank-english-v3.0",
                top_n=config.return_top,
            )

            return [
                RankedResult(
                    original_rank=r.index + 1,
                    score=r.relevance_score,
                    content=candidates[r.index].get("content", ""),
                    metadata=candidates[r.index].get("metadata", {}),
                    chunk_id=candidates[r.index].get("chunk_id", ""),
                )
                for r in response.results
            ]
        except ImportError:
            self._logger.warning("cohere_not_installed")
            return self._rerank_fallback(candidates)

    def _rerank_fallback(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[RankedResult]:
        """Fallback: return candidates in original order with decaying scores."""
        return [
            RankedResult(
                original_rank=i + 1,
                score=1.0 / (i + 1),
                content=c.get("content", ""),
                metadata=c.get("metadata", {}),
                chunk_id=c.get("chunk_id", ""),
            )
            for i, c in enumerate(candidates)
        ]
