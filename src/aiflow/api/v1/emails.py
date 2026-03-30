"""Email processing result endpoints."""
from __future__ import annotations

import os
from typing import Any

import asyncpg
import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


class EmailResultItem(BaseModel):
    """Email processing result summary."""
    email_id: str
    subject: str
    sender: str
    received_date: str | None = None
    intent_id: str | None = None
    intent_display_name: str | None = None
    intent_confidence: float = 0.0
    intent_method: str | None = None
    priority_level: int | None = None
    department_name: str | None = None
    queue_name: str | None = None
    entity_count: int = 0
    attachment_count: int = 0
    processing_time_ms: float = 0.0
    status: str = "completed"


class EmailListResponse(BaseModel):
    """List of email processing results."""
    emails: list[EmailResultItem]
    total: int


def _get_db_url() -> str:
    return os.getenv(
        "AIFLOW_DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )


@router.get("", response_model=EmailListResponse)
async def list_emails(
    intent: str | None = Query(None, description="Filter by intent_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EmailListResponse:
    """List email processing results.

    Queries workflow_runs where skill_name='email_intent_processor'
    and extracts result data from output_data JSONB.
    """
    emails: list[EmailResultItem] = []
    total = 0

    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
            where = "WHERE r.skill_name = 'email_intent_processor' AND r.status = 'completed'"
            params: list[Any] = []
            idx = 1

            if intent:
                where += f" AND r.output_data->>'intent_id' = ${idx}"
                params.append(intent)
                idx += 1

            count_row = await conn.fetchrow(
                f"SELECT COUNT(*) AS cnt FROM workflow_runs r {where}",
                *params,
            )
            total = count_row["cnt"] if count_row else 0

            params.extend([limit, offset])
            rows = await conn.fetch(
                f"""
                SELECT r.id, r.output_data, r.started_at, r.total_duration_ms
                FROM workflow_runs r
                {where}
                ORDER BY r.started_at DESC NULLS LAST
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params,
            )

            for row in rows:
                data = row["output_data"] or {}
                intent_data = data.get("intent") or {}
                priority_data = data.get("priority") or {}
                routing_data = data.get("routing") or {}
                entities_data = data.get("entities") or {}

                emails.append(EmailResultItem(
                    email_id=data.get("email_id", str(row["id"])),
                    subject=data.get("subject", ""),
                    sender=data.get("sender", ""),
                    received_date=row["started_at"].isoformat() if row["started_at"] else None,
                    intent_id=intent_data.get("intent_id"),
                    intent_display_name=intent_data.get("intent_display_name"),
                    intent_confidence=intent_data.get("confidence", 0.0),
                    intent_method=intent_data.get("method"),
                    priority_level=priority_data.get("priority_level"),
                    department_name=routing_data.get("department_name"),
                    queue_name=routing_data.get("queue_name"),
                    entity_count=entities_data.get("entity_count", 0),
                    attachment_count=data.get("attachment_count", 0),
                    processing_time_ms=row["total_duration_ms"] or 0.0,
                ))
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("emails_db_failed", error=str(e))

    return EmailListResponse(emails=emails, total=total)
