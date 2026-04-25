"""Contracts for the nightly RAG retrieval-quality harness.

Sprint S / S145 (SS-FU-3) — operability close-out for the multi-tenant
vector DB. The harness measures MRR@5 + p95 latency on a curated query
set and emits ``CollectionMetrics`` rows that downstream Grafana / a CI
job can persist or alert on.

Relevance is matched at *document title* granularity, not chunk-id —
because the harness runs against operator-seeded collections (e.g.
``aszf_rag_chat``) where chunk IDs are not deterministic across
re-ingests, but document titles are stable. For chunk-level baselines
see ``tests/integration/services/rag_engine/test_retrieval_baseline.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "QuerySpec",
    "CollectionMetrics",
    "HARNESS_VERSION",
]

HARNESS_VERSION = "s145.1"


class QuerySpec(BaseModel):
    """One question + the set of document titles that should appear in top-5."""

    question: str = Field(min_length=1)
    expected_doc_titles: list[str] = Field(min_length=1)

    @field_validator("expected_doc_titles")
    @classmethod
    def _strip_and_dedupe(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for title in value:
            stripped = title.strip()
            if stripped and stripped not in seen:
                seen.append(stripped)
        if not seen:
            raise ValueError("expected_doc_titles must contain at least one non-empty title")
        return seen


class CollectionMetrics(BaseModel):
    """Outcome of one harness run over a single collection."""

    collection_id: str
    mrr5: float
    p95_latency_ms: float
    query_count: int = Field(ge=0)
    measured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    harness_version: str = HARNESS_VERSION

    def to_jsonl(self) -> str:
        """Single-line JSON for nightly persistence."""
        return self.model_dump_json()
