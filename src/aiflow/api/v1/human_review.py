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
