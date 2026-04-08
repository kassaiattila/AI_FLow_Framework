"""
@test_registry:
    suite: unit
    component: aiflow.vectorstore.pgvector_store
    covers: [src/aiflow/vectorstore/pgvector_store.py]
    phase: B3.5
    priority: critical
    estimated_duration_ms: 50
    requires_services: []
    tags: [bm25, normalization, vectorstore]
"""

from __future__ import annotations

from aiflow.vectorstore.pgvector_store import _bm25_score


class TestBM25Normalization:
    def test_empty_query_returns_zero(self) -> None:
        assert _bm25_score([], "any document body here") == 0.0

    def test_no_match_returns_zero(self) -> None:
        """Query terms that don't appear in text yield 0.0."""
        assert _bm25_score(["unicorn"], "invoice total amount") == 0.0

    def test_score_always_in_unit_interval(self) -> None:
        """Any single-term match stays strictly within [0, 1)."""
        doc = "invoice number 123 invoice total invoice date invoice amount"
        score = _bm25_score(["invoice"], doc)
        assert 0.0 <= score < 1.0

    def test_heavy_repetition_still_bounded(self) -> None:
        """High TF must NOT overflow the [0, 1] range (saturation works)."""
        # Repeat the query term 500 times in a short doc → raw BM25 > 10
        doc = "invoice " * 500
        score = _bm25_score(["invoice"], doc)
        assert 0.0 <= score < 1.0, f"score {score} not saturated"
        # Should be close to 1.0 but never reach it
        assert score > 0.7

    def test_combined_score_stays_bounded(self) -> None:
        """Hybrid 0.6·cosine + 0.4·bm25 must never exceed 1.0."""
        doc = "invoice " * 500
        bm25 = _bm25_score(["invoice"], doc)
        cosine = 1.0  # worst case — perfect cosine
        combined = 0.6 * cosine + 0.4 * bm25
        assert combined <= 1.0, f"combined {combined} > 1.0"

    def test_more_matches_score_higher(self) -> None:
        """Saturation must still preserve monotonic ordering."""
        low = _bm25_score(["invoice"], "invoice total here")
        high = _bm25_score(["invoice"], "invoice invoice invoice total invoice")
        assert 0.0 < low < high < 1.0

    def test_custom_avg_dl_parameter(self) -> None:
        """avg_dl is now configurable (was hardcoded 200.0)."""
        doc = "invoice total"
        short_avg = _bm25_score(["invoice"], doc, avg_dl=50.0)
        long_avg = _bm25_score(["invoice"], doc, avg_dl=2000.0)
        # Different avg_dl values should produce different scores
        # (unless corner cases collapse to 0.0)
        assert short_avg != long_avg or (short_avg == 0.0 and long_avg == 0.0)
        # Both must still be in [0, 1)
        assert 0.0 <= short_avg < 1.0
        assert 0.0 <= long_avg < 1.0
