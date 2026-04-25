"""Nightly RAG retrieval-quality harness.

Wraps an existing ``RAGEngineService`` (or any object exposing the same
``async def query(collection_id, question, ...) -> QueryResult``
contract) and computes MRR@5 + p95 latency over a curated query set.

The harness is intentionally provider-agnostic: it only depends on the
shape of ``QueryResult`` (``response_time_ms`` + ``sources[i].document_title``).
This keeps the unit tests free of pgvector / Langfuse / OpenAI.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import structlog

from .contracts import HARNESS_VERSION, CollectionMetrics, QuerySpec

__all__ = [
    "RagMetricsHarness",
    "compute_mrr_at_k",
    "compute_p95",
]

logger = structlog.get_logger(__name__)

QueryFn = Callable[[str, str], Awaitable[Any]]


def compute_mrr_at_k(
    retrieved_titles: Sequence[str], expected_titles: Sequence[str], k: int = 5
) -> float:
    """Reciprocal rank of the first relevant doc in the top-``k`` retrieved titles.

    Returns 0.0 when no expected title appears in the top-``k`` slice.
    """
    expected_set = {t for t in expected_titles if t}
    for position, title in enumerate(retrieved_titles[:k], start=1):
        if title in expected_set:
            return 1.0 / position
    return 0.0


def compute_p95(samples: Sequence[float]) -> float:
    """Linear-interpolated p95 over a non-empty sample list."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    rank = 0.95 * (len(ordered) - 1)
    lower_idx = int(math.floor(rank))
    upper_idx = int(math.ceil(rank))
    if lower_idx == upper_idx:
        return ordered[lower_idx]
    weight = rank - lower_idx
    return ordered[lower_idx] * (1 - weight) + ordered[upper_idx] * weight


class RagMetricsHarness:
    """Compute retrieval-quality metrics for a single collection.

    Usage::

        harness = RagMetricsHarness(query_fn=rag_service.query)
        metrics = await harness.measure_collection("coll-abc", query_set)
        print(metrics.to_jsonl())
    """

    def __init__(self, query_fn: QueryFn, *, top_k: int = 5) -> None:
        self._query_fn = query_fn
        self._top_k = top_k

    async def measure_collection(
        self,
        collection_id: str,
        query_set: Sequence[QuerySpec],
    ) -> CollectionMetrics:
        if not query_set:
            logger.info(
                "rag_metrics_empty_query_set",
                collection_id=collection_id,
                harness_version=HARNESS_VERSION,
            )
            return CollectionMetrics(
                collection_id=collection_id,
                mrr5=0.0,
                p95_latency_ms=0.0,
                query_count=0,
            )

        rr_scores: list[float] = []
        latencies: list[float] = []

        for spec in query_set:
            result = await self._query_fn(collection_id, spec.question)
            sources = getattr(result, "sources", []) or []
            titles = [str(s.get("document_title", "")) for s in sources if isinstance(s, dict)]
            rr_scores.append(compute_mrr_at_k(titles, spec.expected_doc_titles, k=self._top_k))
            latencies.append(float(getattr(result, "response_time_ms", 0.0)))

        mrr5 = sum(rr_scores) / len(rr_scores)
        p95 = compute_p95(latencies)

        metrics = CollectionMetrics(
            collection_id=collection_id,
            mrr5=mrr5,
            p95_latency_ms=p95,
            query_count=len(query_set),
        )
        logger.info(
            "rag_metrics_measured",
            collection_id=collection_id,
            mrr5=round(mrr5, 4),
            p95_latency_ms=round(p95, 2),
            query_count=len(query_set),
            harness_version=HARNESS_VERSION,
        )
        return metrics
