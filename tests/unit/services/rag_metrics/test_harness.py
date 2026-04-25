"""Unit tests — RagMetricsHarness (Sprint S / S145, SS-FU-3).

@test_registry
suite: unit-services
component: aiflow.services.rag_metrics
covers:
  - src/aiflow/services/rag_metrics/contracts.py
  - src/aiflow/services/rag_metrics/harness.py
phase: v1.5.2
priority: high
tags: [unit, services, rag_metrics, sprint_s, s145]
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from aiflow.services.rag_metrics import (
    HARNESS_VERSION,
    CollectionMetrics,
    QuerySpec,
    RagMetricsHarness,
    compute_mrr_at_k,
    compute_p95,
)


def _result(titles: list[str], latency_ms: float = 100.0) -> SimpleNamespace:
    return SimpleNamespace(
        sources=[{"document_title": t} for t in titles],
        response_time_ms=latency_ms,
    )


def test_compute_mrr_at_k_basic_ties_and_no_hits() -> None:
    assert compute_mrr_at_k(["A", "B", "C"], ["A"]) == 1.0
    assert compute_mrr_at_k(["X", "A", "B"], ["A"]) == 0.5
    assert compute_mrr_at_k(["X", "Y", "A"], ["A"]) == pytest.approx(1 / 3)
    assert compute_mrr_at_k(["A", "B"], ["A", "B"]) == 1.0
    assert compute_mrr_at_k(["X", "Y", "Z", "Q", "P"], ["A"]) == 0.0
    assert compute_mrr_at_k(["X", "Y", "Z", "Q", "P", "A"], ["A"], k=5) == 0.0
    assert compute_mrr_at_k([], ["A"]) == 0.0


def test_compute_p95_over_20_samples() -> None:
    samples = list(range(1, 21))
    p95 = compute_p95(samples)
    assert 18.0 <= p95 <= 20.0
    assert compute_p95([42.0]) == 42.0
    assert compute_p95([]) == 0.0


def test_query_spec_validates_non_empty_doc_list() -> None:
    QuerySpec(question="q", expected_doc_titles=["doc-a"])
    with pytest.raises(ValidationError):
        QuerySpec(question="q", expected_doc_titles=[])
    with pytest.raises(ValidationError):
        QuerySpec(question="q", expected_doc_titles=["", "  "])
    deduped = QuerySpec(
        question="q",
        expected_doc_titles=[" doc-a ", "doc-a", "doc-b"],
    )
    assert deduped.expected_doc_titles == ["doc-a", "doc-b"]


def test_collection_metrics_jsonl_emission_shape() -> None:
    metrics = CollectionMetrics(
        collection_id="abc",
        mrr5=0.625,
        p95_latency_ms=210.5,
        query_count=4,
    )
    payload = json.loads(metrics.to_jsonl())
    assert payload["collection_id"] == "abc"
    assert payload["mrr5"] == 0.625
    assert payload["p95_latency_ms"] == 210.5
    assert payload["query_count"] == 4
    assert payload["harness_version"] == HARNESS_VERSION
    assert "measured_at" in payload


async def test_harness_iterates_over_query_set_and_aggregates() -> None:
    query_set = [
        QuerySpec(question="q1", expected_doc_titles=["doc-a"]),
        QuerySpec(question="q2", expected_doc_titles=["doc-b"]),
        QuerySpec(question="q3", expected_doc_titles=["doc-c"]),
    ]
    responses = {
        "q1": _result(["doc-a", "x"], latency_ms=120),
        "q2": _result(["x", "doc-b"], latency_ms=200),
        "q3": _result(["x", "y", "z", "q", "p"], latency_ms=300),
    }
    seen_collection_ids: list[str] = []

    async def fake_query(collection_id: str, question: str) -> SimpleNamespace:
        seen_collection_ids.append(collection_id)
        return responses[question]

    harness = RagMetricsHarness(query_fn=fake_query)
    metrics = await harness.measure_collection("coll-1", query_set)

    assert seen_collection_ids == ["coll-1", "coll-1", "coll-1"]
    assert metrics.query_count == 3
    assert metrics.mrr5 == pytest.approx((1.0 + 0.5 + 0.0) / 3)
    assert 200.0 <= metrics.p95_latency_ms <= 300.0


async def test_harness_empty_query_set_returns_sentinel() -> None:
    calls = 0

    async def fake_query(collection_id: str, question: str) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        return _result(["doc-a"])

    harness = RagMetricsHarness(query_fn=fake_query)
    metrics = await harness.measure_collection("empty-coll", [])

    assert metrics.collection_id == "empty-coll"
    assert metrics.query_count == 0
    assert metrics.mrr5 == 0.0
    assert metrics.p95_latency_ms == 0.0
    assert calls == 0
