"""
@test_registry:
    suite: unit
    component: aiflow.engine.confidence_router
    covers: [src/aiflow/engine/confidence_router.py]
    phase: B3.5
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [confidence, routing, engine]
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aiflow.engine.confidence import DocumentConfidence, FieldConfidence
from aiflow.engine.confidence_router import (
    ConfidenceRoutingConfig,
    RoutingDecision,
    RoutingResult,
    route_by_confidence,
)


def _make_doc(
    overall: float,
    *,
    field_scores: list[tuple[str, float]] | None = None,
    missing: list[str] | None = None,
) -> DocumentConfidence:
    """Build a minimal DocumentConfidence for routing tests."""
    scores = [
        FieldConfidence(field_name=name, value="x", confidence=conf, factors={})
        for name, conf in (field_scores or [])
    ]
    return DocumentConfidence(
        overall=overall,
        field_scores=scores,
        structural_penalty=1.0,
        source_quality=1.0,
        missing_mandatory=missing or [],
    )


@pytest.fixture
def default_config() -> ConfidenceRoutingConfig:
    return ConfidenceRoutingConfig()


class TestConfigValidation:
    def test_defaults(self) -> None:
        cfg = ConfidenceRoutingConfig()
        assert cfg.auto_approve_threshold == 0.90
        assert cfg.review_threshold == 0.70
        assert cfg.reject_threshold == 0.50

    def test_thresholds_must_be_ordered(self) -> None:
        """reject <= review <= auto must hold."""
        with pytest.raises(ValueError, match="Thresholds must satisfy"):
            ConfidenceRoutingConfig(
                auto_approve_threshold=0.70,
                review_threshold=0.90,  # Out of order
                reject_threshold=0.50,
            )


class TestRoutingDecisions:
    async def test_auto_approved_high_score(self, default_config: ConfidenceRoutingConfig) -> None:
        """score >= 0.90 → AUTO_APPROVED, no review created."""
        doc = _make_doc(0.95)
        result = await route_by_confidence(doc, default_config, review_service=None)
        assert isinstance(result, RoutingResult)
        assert result.decision == RoutingDecision.AUTO_APPROVED
        assert result.score == 0.95
        assert result.review_id is None

    async def test_sent_to_review_mid_score(self, default_config: ConfidenceRoutingConfig) -> None:
        """0.70 <= score < 0.90 → SENT_TO_REVIEW."""
        doc = _make_doc(0.80)
        result = await route_by_confidence(doc, default_config, review_service=None)
        assert result.decision == RoutingDecision.SENT_TO_REVIEW
        assert result.score == 0.80

    async def test_rejected_for_review_low_score(
        self, default_config: ConfidenceRoutingConfig
    ) -> None:
        """score < 0.50 → REJECTED_FOR_REVIEW (high priority)."""
        doc = _make_doc(0.40)
        result = await route_by_confidence(doc, default_config, review_service=None)
        assert result.decision == RoutingDecision.REJECTED_FOR_REVIEW
        assert result.score == 0.40

    async def test_between_review_and_reject_is_rejected(
        self, default_config: ConfidenceRoutingConfig
    ) -> None:
        """0.50 <= score < 0.70 also routed to reject band (review required)."""
        doc = _make_doc(0.60)
        result = await route_by_confidence(doc, default_config, review_service=None)
        assert result.decision == RoutingDecision.REJECTED_FOR_REVIEW

    async def test_exact_auto_approve_threshold(
        self, default_config: ConfidenceRoutingConfig
    ) -> None:
        """score == auto_approve_threshold is still AUTO_APPROVED (inclusive)."""
        doc = _make_doc(0.90)
        result = await route_by_confidence(doc, default_config)
        assert result.decision == RoutingDecision.AUTO_APPROVED

    async def test_exact_review_threshold(self, default_config: ConfidenceRoutingConfig) -> None:
        """score == review_threshold is SENT_TO_REVIEW (inclusive)."""
        doc = _make_doc(0.70)
        result = await route_by_confidence(doc, default_config)
        assert result.decision == RoutingDecision.SENT_TO_REVIEW


class TestReviewServiceIntegration:
    async def test_review_service_called_for_sent_to_review(
        self, default_config: ConfidenceRoutingConfig
    ) -> None:
        """Mid-confidence score → review_service.create_review invoked."""
        mock_item = type("obj", (), {"id": "review-123"})()
        mock_service = AsyncMock()
        mock_service.create_review = AsyncMock(return_value=mock_item)

        doc = _make_doc(
            0.80,
            field_scores=[
                ("invoice_number", 0.95),
                ("invoice_date", 0.60),  # low confidence
                ("vendor_name", 0.50),  # low confidence
            ],
        )
        result = await route_by_confidence(
            doc,
            default_config,
            review_service=mock_service,
            entity_type="invoice",
            entity_id="inv-42",
            document_title="Test Invoice",
        )
        assert result.decision == RoutingDecision.SENT_TO_REVIEW
        assert result.review_id == "review-123"

        mock_service.create_review.assert_awaited_once()
        call_kwargs = mock_service.create_review.await_args.kwargs
        assert call_kwargs["entity_type"] == "invoice"
        assert call_kwargs["entity_id"] == "inv-42"
        assert call_kwargs["priority"] == "normal"
        assert "Test Invoice" in call_kwargs["title"]
        metadata = call_kwargs["metadata"]
        assert metadata["confidence"] == 0.80
        assert set(metadata["low_confidence_fields"]) == {"invoice_date", "vendor_name"}

    async def test_review_service_called_for_reject_high_priority(
        self, default_config: ConfidenceRoutingConfig
    ) -> None:
        """Low-confidence score → create_review with priority="high"."""
        mock_item = type("obj", (), {"id": "review-999"})()
        mock_service = AsyncMock()
        mock_service.create_review = AsyncMock(return_value=mock_item)

        doc = _make_doc(0.30, missing=["invoice_number", "gross_total"])
        result = await route_by_confidence(
            doc,
            default_config,
            review_service=mock_service,
            entity_id="inv-bad",
            document_title="Broken Doc",
        )
        assert result.decision == RoutingDecision.REJECTED_FOR_REVIEW

        mock_service.create_review.assert_awaited_once()
        call_kwargs = mock_service.create_review.await_args.kwargs
        assert call_kwargs["priority"] == "high"
        assert "LOW CONFIDENCE" in call_kwargs["title"]
        metadata = call_kwargs["metadata"]
        assert metadata["confidence"] == 0.30
        assert metadata["reason"] == "below_reject_threshold"
        assert set(metadata["missing_mandatory"]) == {"invoice_number", "gross_total"}

    async def test_no_review_service_still_returns_decision(
        self, default_config: ConfidenceRoutingConfig
    ) -> None:
        """review_service=None → decision OK, no DB side effects."""
        doc = _make_doc(0.80)
        result = await route_by_confidence(doc, default_config, review_service=None)
        assert result.decision == RoutingDecision.SENT_TO_REVIEW
        assert result.review_id is None
