"""Hybrid search engine combining vector similarity and keyword (BM25) search with RRF fusion."""
from typing import Any
import structlog
from aiflow.vectorstore.base import VectorStore, SearchResult, SearchFilter

__all__ = ["HybridSearchEngine"]
logger = structlog.get_logger(__name__)

class HybridSearchEngine:
    """Combines vector search + keyword search using Reciprocal Rank Fusion (RRF).

    RRF formula: score = sum(1 / (k + rank_i)) for each ranking system
    """

    def __init__(self, vector_store: VectorStore, *,
                 vector_weight: float = 0.6, keyword_weight: float = 0.4,
                 rrf_k: int = 60) -> None:
        self._store = vector_store
        self._vector_weight = vector_weight
        self._keyword_weight = keyword_weight
        self._rrf_k = rrf_k

    async def search(self, collection: str, skill_name: str,
                     query_embedding: list[float], query_text: str | None = None,
                     top_k: int = 10, filters: SearchFilter | None = None) -> list[SearchResult]:
        """Execute hybrid search (vector + keyword) with RRF fusion."""
        # Get results from vector store (it handles hybrid internally if supported)
        results = await self._store.search(
            collection=collection,
            skill_name=skill_name,
            query_embedding=query_embedding,
            query_text=query_text,
            top_k=top_k * 2,  # Fetch more for RRF re-ranking
            filters=filters,
            search_mode="hybrid" if query_text else "vector",
        )

        if not query_text or len(results) <= top_k:
            return results[:top_k]

        # Apply RRF if we have both vector and keyword scores
        reranked = self._apply_rrf(results)
        logger.info("hybrid_search_completed", collection=collection,
                     results=len(reranked[:top_k]), query_len=len(query_text or ""))
        return reranked[:top_k]

    def _apply_rrf(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply Reciprocal Rank Fusion to combine vector and keyword rankings."""
        # Separate rankings
        by_vector = sorted(results, key=lambda r: r.vector_score or 0, reverse=True)
        by_keyword = sorted(results, key=lambda r: r.keyword_score or 0, reverse=True)

        # Calculate RRF scores
        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, SearchResult] = {}

        for rank, result in enumerate(by_vector):
            key = str(result.chunk_id)
            chunk_map[key] = result
            rrf_scores[key] = rrf_scores.get(key, 0) + self._vector_weight / (self._rrf_k + rank + 1)

        for rank, result in enumerate(by_keyword):
            key = str(result.chunk_id)
            chunk_map[key] = result
            rrf_scores[key] = rrf_scores.get(key, 0) + self._keyword_weight / (self._rrf_k + rank + 1)

        # Sort by RRF score
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

        return [
            chunk_map[key].model_copy(update={"score": rrf_scores[key]})
            for key in sorted_keys
        ]

    @property
    def vector_weight(self) -> float:
        return self._vector_weight

    @property
    def keyword_weight(self) -> float:
        return self._keyword_weight
