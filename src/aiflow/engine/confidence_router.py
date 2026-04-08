"""Confidence → routing decision engine (B3.5).

Connects ``DocumentConfidence`` scores (from ``engine/confidence.py``)
to the ``HumanReviewService`` queue via explicit thresholds:

    score >= auto_approve_threshold (default 0.90)  → AUTO_APPROVED
    score >= review_threshold       (default 0.70)  → SENT_TO_REVIEW
    score <  reject_threshold       (default 0.50)  → REJECTED_FOR_REVIEW

The routing function accepts an *optional* ``HumanReviewService`` so the
core decision logic can be unit-tested without PostgreSQL. When a service
is provided, review/reject cases create a review row with the confidence
score and list of low-confidence fields in ``metadata``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from aiflow.engine.confidence import DocumentConfidence

if TYPE_CHECKING:
    from aiflow.services.human_review.service import HumanReviewService

__all__ = [
    "ConfidenceRoutingConfig",
    "RoutingDecision",
    "RoutingResult",
    "route_by_confidence",
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RoutingDecision(StrEnum):
    """Terminal routing outcome for an extraction result."""

    AUTO_APPROVED = "auto_approved"
    SENT_TO_REVIEW = "sent_to_review"
    REJECTED_FOR_REVIEW = "rejected_for_review"


class ConfidenceRoutingConfig(BaseModel):
    """Thresholds for confidence → routing decisions.

    Invariant: ``reject_threshold <= review_threshold <= auto_approve_threshold``.
    """

    auto_approve_threshold: float = Field(0.90, ge=0.0, le=1.0)
    review_threshold: float = Field(0.70, ge=0.0, le=1.0)
    reject_threshold: float = Field(0.50, ge=0.0, le=1.0)
    low_confidence_field_threshold: float = Field(
        0.70,
        ge=0.0,
        le=1.0,
        description="Per-field threshold below which a field is flagged as low-confidence.",
    )

    @model_validator(mode="after")
    def _check_order(self) -> ConfidenceRoutingConfig:
        if not (self.reject_threshold <= self.review_threshold <= self.auto_approve_threshold):
            raise ValueError(
                "Thresholds must satisfy "
                "reject_threshold <= review_threshold <= auto_approve_threshold"
            )
        return self


class RoutingResult(BaseModel):
    """Outcome of ``route_by_confidence``."""

    decision: RoutingDecision
    score: float
    review_id: str | None = None
    low_confidence_fields: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


async def route_by_confidence(
    document_confidence: DocumentConfidence,
    config: ConfidenceRoutingConfig,
    *,
    review_service: HumanReviewService | None = None,
    entity_type: str = "extraction",
    entity_id: str = "",
    document_title: str = "Document",
) -> RoutingResult:
    """Map a ``DocumentConfidence`` score to an auto/review/reject decision.

    When the score falls into the review or reject band AND a
    ``review_service`` is provided, a row is created in the human review
    queue with the confidence score and list of low-confidence fields.

    If ``review_service`` is ``None`` the decision is returned without
    any DB side effects — this is the supported mode for unit tests.
    """
    score = document_confidence.overall

    low_confidence_fields = [
        f.field_name
        for f in document_confidence.field_scores
        if f.confidence < config.low_confidence_field_threshold
    ]

    if score >= config.auto_approve_threshold:
        return RoutingResult(
            decision=RoutingDecision.AUTO_APPROVED,
            score=score,
            low_confidence_fields=low_confidence_fields,
        )

    if score >= config.review_threshold:
        review_id = await _create_review(
            review_service=review_service,
            entity_type=entity_type,
            entity_id=entity_id,
            title=f"Review: {document_title}",
            priority="normal",
            metadata={
                "confidence": score,
                "low_confidence_fields": low_confidence_fields,
                "structural_penalty": document_confidence.structural_penalty,
                "missing_mandatory": document_confidence.missing_mandatory,
            },
        )
        return RoutingResult(
            decision=RoutingDecision.SENT_TO_REVIEW,
            score=score,
            review_id=review_id,
            low_confidence_fields=low_confidence_fields,
        )

    # score < review_threshold → reject band (includes the < reject_threshold zone)
    review_id = await _create_review(
        review_service=review_service,
        entity_type=entity_type,
        entity_id=entity_id,
        title=f"LOW CONFIDENCE: {document_title}",
        priority="high",
        metadata={
            "confidence": score,
            "reason": "below_reject_threshold"
            if score < config.reject_threshold
            else "below_review_threshold",
            "low_confidence_fields": low_confidence_fields,
            "missing_mandatory": document_confidence.missing_mandatory,
        },
    )
    return RoutingResult(
        decision=RoutingDecision.REJECTED_FOR_REVIEW,
        score=score,
        review_id=review_id,
        low_confidence_fields=low_confidence_fields,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _create_review(
    *,
    review_service: HumanReviewService | None,
    entity_type: str,
    entity_id: str,
    title: str,
    priority: str,
    metadata: dict,
) -> str | None:
    """Best-effort review row creation. Returns review_id or None."""
    if review_service is None:
        return None

    item = await review_service.create_review(
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        priority=priority,
        metadata=metadata,
    )
    return getattr(item, "id", None)
