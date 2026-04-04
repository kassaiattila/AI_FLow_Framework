"""Hybrid search engine combining vector similarity and keyword (BM25) search with RRF fusion.

Supports three search modes:
  - vector: cosine similarity only (pgvector <-> operator)
  - keyword: BM25 tsvector full-text only
  - hybrid (default): both, merged via Reciprocal Rank Fusion (RRF)

Configurable via SearchConfig Pydantic model.
"""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from aiflow.vectorstore.base import SearchFilter, SearchResult, VectorStore

__all__ = ["HybridSearchEngine", "SearchConfig"]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------

class SearchConfig(BaseModel):
    """Configuration for hybrid search behavior."""

    vector_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for vector (semantic) scores in RRF fusion.",
    )
    keyword_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for keyword (BM25) scores in RRF fusion.",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Maximum number of results to return.",
    )
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to include in results (0 = no filter).",
    )
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="RRF constant k (controls rank smoothing, standard=60).",
    )
    search_mode: str = Field(
        default="hybrid",
        description="Search mode: 'vector', 'keyword', or 'hybrid'.",
    )
    rerank: bool = Field(
        default=False,
        description="Whether to apply a cross-encoder reranker (future).",
    )
    rerank_model: str | None = Field(
        default=None,
        description="Model name for cross-encoder reranking (requires rerank=True).",
    )
    fetch_multiplier: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Multiplier for top_k when fetching candidates for RRF re-ranking.",
    )


# ---------------------------------------------------------------------------
# Hybrid search engine
# ---------------------------------------------------------------------------

class HybridSearchEngine:
    """Combines vector search + keyword search using Reciprocal Rank Fusion (RRF).

    RRF formula: score = sum(weight_i / (k + rank_i)) for each ranking system.

    Usage::

        engine = HybridSearchEngine(store, vector_weight=0.6, keyword_weight=0.4)
        results = await engine.search("coll", "skill", embedding, "search text")

    Or with SearchConfig::

        config = SearchConfig(vector_weight=0.7, keyword_weight=0.3, top_k=20)
        engine = HybridSearchEngine.from_config(store, config)
    """

    def __init__(
        self,
        vector_store: VectorStore,
        *,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        rrf_k: int = 60,
        similarity_threshold: float = 0.0,
        fetch_multiplier: int = 3,
    ) -> None:
        self._store = vector_store
        self._vector_weight = vector_weight
        self._keyword_weight = keyword_weight
        self._rrf_k = rrf_k
        self._similarity_threshold = similarity_threshold
        self._fetch_multiplier = fetch_multiplier

    @classmethod
    def from_config(
        cls, vector_store: VectorStore, config: SearchConfig
    ) -> HybridSearchEngine:
        """Create engine from a SearchConfig model."""
        return cls(
            vector_store,
            vector_weight=config.vector_weight,
            keyword_weight=config.keyword_weight,
            rrf_k=config.rrf_k,
            similarity_threshold=config.similarity_threshold,
            fetch_multiplier=config.fetch_multiplier,
        )

    # ------------------------------------------------------------------
    # Main search
    # ------------------------------------------------------------------

    async def search(
        self,
        collection: str,
        skill_name: str,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 10,
        filters: SearchFilter | None = None,
    ) -> list[SearchResult]:
        """Execute hybrid search (vector + keyword) with RRF fusion.

        Steps:
            1. Determine search mode (hybrid if query_text provided, else vector-only).
            2. Fetch candidates from vector store (with fetch_multiplier for re-ranking headroom).
            3. If hybrid, apply RRF fusion to combine vector and keyword rankings.
            4. Apply similarity threshold filter.
            5. Return top_k results.
        """
        search_mode = "hybrid" if query_text else "vector"
        fetch_count = top_k * self._fetch_multiplier if query_text else top_k

        # Get results from vector store (it handles hybrid internally if supported)
        results = await self._store.search(
            collection=collection,
            skill_name=skill_name,
            query_embedding=query_embedding,
            query_text=query_text,
            top_k=fetch_count,
            filters=filters,
            search_mode=search_mode,
        )

        if not results:
            logger.info("hybrid_search_empty", collection=collection, mode=search_mode)
            return []

        # Vector-only or too few results -- skip RRF
        if not query_text or len(results) <= top_k:
            filtered = self._apply_threshold(results)
            return filtered[:top_k]

        # Apply RRF if we have both vector and keyword scores
        reranked = self._apply_rrf(results)

        # Apply similarity threshold
        filtered = self._apply_threshold(reranked)

        logger.info(
            "hybrid_search_completed",
            collection=collection,
            mode=search_mode,
            candidates=len(results),
            after_rrf=len(reranked),
            after_threshold=len(filtered),
            returned=min(len(filtered), top_k),
            query_len=len(query_text or ""),
        )
        return filtered[:top_k]

    # ------------------------------------------------------------------
    # RRF fusion
    # ------------------------------------------------------------------

    def _apply_rrf(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply Reciprocal Rank Fusion to combine vector and keyword rankings.

        Each result gets a fused score based on its rank in each sub-ranking:
            rrf_score = w_v / (k + rank_vector) + w_k / (k + rank_keyword)

        Results without a keyword_score only get the vector component (and vice
        versa), so pure-vector results are not penalized.
        """
        # Separate rankings
        by_vector = sorted(results, key=lambda r: r.vector_score or 0.0, reverse=True)
        by_keyword = sorted(results, key=lambda r: r.keyword_score or 0.0, reverse=True)

        # Calculate RRF scores
        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, SearchResult] = {}

        for rank, result in enumerate(by_vector):
            key = str(result.chunk_id)
            chunk_map[key] = result
            rrf_scores[key] = rrf_scores.get(key, 0.0) + self._vector_weight / (
                self._rrf_k + rank + 1
            )

        for rank, result in enumerate(by_keyword):
            key = str(result.chunk_id)
            chunk_map[key] = result
            rrf_scores[key] = rrf_scores.get(key, 0.0) + self._keyword_weight / (
                self._rrf_k + rank + 1
            )

        # Sort by RRF score descending
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

        return [
            chunk_map[key].model_copy(update={"score": rrf_scores[key]})
            for key in sorted_keys
        ]

    # ------------------------------------------------------------------
    # Threshold filter
    # ------------------------------------------------------------------

    def _apply_threshold(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove results below the similarity threshold."""
        if self._similarity_threshold <= 0.0:
            return results
        return [r for r in results if r.score >= self._similarity_threshold]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def vector_weight(self) -> float:
        return self._vector_weight

    @property
    def keyword_weight(self) -> float:
        return self._keyword_weight

    @property
    def rrf_k(self) -> int:
        return self._rrf_k

    @property
    def similarity_threshold(self) -> float:
        return self._similarity_threshold
