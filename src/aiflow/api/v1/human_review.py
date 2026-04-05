"""Human Review API — pending queue + approve/reject + history."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from functools import cache
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@cache
def _get_service():
    from aiflow.services.human_review import HumanReviewService
    return HumanReviewService()


class ReviewCreateRequest(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    description: str | None = None
    priority: str = "normal"
    metadata: dict[str, Any] | None = None


class ReviewDecisionRequest(BaseModel):
    reviewer: str = "admin"
    comment: str | None = None


class ReviewResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    reviewer: str | None = None
    comment: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: str = ""
    reviewed_at: str | None = None
    source: str = "backend"


class ReviewListResponse(BaseModel):
    reviews: list[ReviewResponse]
    total: int
    source: str = "backend"


@router.get("/pending", response_model=ReviewListResponse)
async def list_pending(limit: int = 50):
    svc = _get_service()
    items = await svc.list_pending(limit=limit)
    return ReviewListResponse(
        reviews=[ReviewResponse(**i.model_dump(), source="backend") for i in items],
        total=len(items),
    )


@router.get("/history", response_model=ReviewListResponse)
async def list_history(limit: int = 50):
    svc = _get_service()
    items = await svc.list_history(limit=limit)
    return ReviewListResponse(
        reviews=[ReviewResponse(**i.model_dump(), source="backend") for i in items],
        total=len(items),
    )


@router.post("", response_model=ReviewResponse, status_code=201)
async def create_review(request: ReviewCreateRequest):
    svc = _get_service()
    try:
        item = await svc.create_review(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            title=request.title,
            description=request.description,
            priority=request.priority,
            metadata=request.metadata,
        )
        return ReviewResponse(**item.model_dump(), source="backend")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
    svc = _get_service()
    item = await svc.get_review(review_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewResponse(**item.model_dump(), source="backend")


@router.post("/{review_id}/approve", response_model=ReviewResponse)
async def approve_review(review_id: str, request: ReviewDecisionRequest):
    svc = _get_service()
    item = await svc.approve(review_id, reviewer=request.reviewer, comment=request.comment)
    if not item:
        raise HTTPException(status_code=404, detail="Review not found or already decided")
    return ReviewResponse(**item.model_dump(), source="backend")


@router.post("/{review_id}/reject", response_model=ReviewResponse)
async def reject_review(review_id: str, request: ReviewDecisionRequest):
    svc = _get_service()
    item = await svc.reject(review_id, reviewer=request.reviewer, comment=request.comment)
    if not item:
        raise HTTPException(status_code=404, detail="Review not found or already decided")
    return ReviewResponse(**item.model_dump(), source="backend")


# ---------------------------------------------------------------------------
# SLA Escalation endpoints (S12)
# ---------------------------------------------------------------------------


class EscalateRequest(BaseModel):
    reason: str = "Manual escalation"


class SlaCheckRequest(BaseModel):
    sla_hours: float = 24.0


class SlaCheckResponse(BaseModel):
    overdue_count: int
    escalated_count: int
    escalated_ids: list[str] = Field(default_factory=list)
    source: str = "backend"


@router.post("/{review_id}/escalate", response_model=ReviewResponse)
async def escalate_review(review_id: str, request: EscalateRequest):
    """Manually escalate a pending review — bumps priority."""
    svc = _get_service()
    item = await svc.escalate(review_id, reason=request.reason)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Review not found or already decided",
        )
    return ReviewResponse(**item.model_dump(), source="backend")


@router.get("/sla/overdue", response_model=ReviewListResponse)
async def list_overdue_reviews(sla_hours: float = 24.0):
    """List pending reviews that have exceeded their SLA deadline."""
    svc = _get_service()
    items = await svc.check_sla_deadlines(sla_hours=sla_hours)
    return ReviewListResponse(
        reviews=[ReviewResponse(**i.model_dump(), source="backend") for i in items],
        total=len(items),
    )


@router.post("/sla/check-and-escalate", response_model=SlaCheckResponse)
async def check_and_escalate(request: SlaCheckRequest):
    """Check SLA deadlines and auto-escalate overdue reviews."""
    svc = _get_service()
    overdue = await svc.check_sla_deadlines(sla_hours=request.sla_hours)
    escalated = await svc.check_and_escalate(sla_hours=request.sla_hours)
    return SlaCheckResponse(
        overdue_count=len(overdue),
        escalated_count=len(escalated),
        escalated_ids=[r.id for r in escalated],
    )
