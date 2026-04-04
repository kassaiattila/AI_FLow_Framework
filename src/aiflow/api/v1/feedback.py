"""User feedback API for RAG query quality improvement."""
from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool

__all__ = ["router"]

router = APIRouter(prefix="/v1", tags=["feedback"])
logger = structlog.get_logger(__name__)


class FeedbackRequest(BaseModel):
    """Feedback submission for a RAG query result."""
    query_id: str = ""
    collection: str = "default"
    question: str = ""
    answer: str = ""
    score: int = Field(ge=1, le=5, default=3)
    thumbs_up: bool | None = None
    comment: str = ""


class FeedbackResponse(BaseModel):
    """Response after feedback submission."""
    success: bool = True
    message: str = "Feedback saved"


class FeedbackStatsItem(BaseModel):
    """Feedback statistics for a single collection."""
    collection: str
    total_feedback: int = 0
    avg_score: float = 0.0
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0


class FeedbackStatsResponse(BaseModel):
    """Aggregated feedback statistics."""
    stats: list[FeedbackStatsItem] = []


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Submit user feedback for a RAG query result.

    Stores feedback in the rag_query_log table. If DB is unavailable,
    feedback is logged via structlog and a success response is still returned
    (best-effort persistence).
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO rag_query_log
                    (collection, question, answer, role, customer)
                VALUES ($1, $2, $3, $4, $5)
                """,
                request.collection,
                request.question,
                request.answer,
                f"feedback:{request.score}",
                request.comment,
            )
    except Exception as e:
        logger.warning("feedback_db_failed", error=str(e))

    logger.info(
        "feedback_received",
        collection=request.collection,
        score=request.score,
        thumbs=request.thumbs_up,
    )
    return FeedbackResponse()


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def feedback_stats() -> FeedbackStatsResponse:
    """Get aggregated feedback statistics per collection.

    Queries rag_query_log for rows where role starts with 'feedback:'
    and aggregates scores per collection.
    """
    items: list[FeedbackStatsItem] = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    collection,
                    COUNT(*) AS total_feedback,
                    AVG(
                        CAST(REPLACE(role, 'feedback:', '') AS INTEGER)
                    ) AS avg_score,
                    SUM(CASE WHEN CAST(REPLACE(role, 'feedback:', '') AS INTEGER) >= 4
                        THEN 1 ELSE 0 END) AS thumbs_up_count,
                    SUM(CASE WHEN CAST(REPLACE(role, 'feedback:', '') AS INTEGER) <= 2
                        THEN 1 ELSE 0 END) AS thumbs_down_count
                FROM rag_query_log
                WHERE role LIKE 'feedback:%'
                GROUP BY collection
                ORDER BY total_feedback DESC
                """
            )
            for row in rows:
                items.append(FeedbackStatsItem(
                    collection=row["collection"],
                    total_feedback=row["total_feedback"],
                    avg_score=round(float(row["avg_score"] or 0), 2),
                    thumbs_up_count=row["thumbs_up_count"] or 0,
                    thumbs_down_count=row["thumbs_down_count"] or 0,
                ))
    except Exception as e:
        logger.warning("feedback_stats_db_failed", error=str(e))

    return FeedbackStatsResponse(stats=items)
