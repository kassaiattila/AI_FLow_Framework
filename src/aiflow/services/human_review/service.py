"""HumanReviewService — pending/approve/reject/history queue with PostgreSQL persistence."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel

__all__ = ["HumanReviewItem", "HumanReviewService"]

logger = structlog.get_logger(__name__)


class HumanReviewItem(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    title: str
    description: str | None = None
    status: str = "pending"
    priority: str = "normal"
    reviewer: str | None = None
    comment: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: str = ""
    reviewed_at: str | None = None


class HumanReviewService:
    """Manages human review queue backed by PostgreSQL."""

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            url = self._db_url or os.getenv(
                "AIFLOW_DATABASE__URL",
                "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
            ).replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
        return self._pool

    async def create_review(
        self,
        entity_type: str,
        entity_id: str,
        title: str,
        description: str | None = None,
        priority: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> HumanReviewItem:
        pool = await self._get_pool()
        review_id = str(uuid.uuid4())
        meta_str = json.dumps(metadata) if metadata else None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO human_review_queue
                   (id, entity_type, entity_id, title, description, priority, metadata_json)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING *""",
                review_id, entity_type, entity_id, title, description, priority, meta_str,
            )
        logger.info("review_created", id=review_id, entity_type=entity_type, entity_id=entity_id)
        return self._row_to_item(row)

    async def list_pending(self, limit: int = 50) -> list[HumanReviewItem]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM human_review_queue
                   WHERE status = 'pending'
                   ORDER BY
                     CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
                     created_at ASC
                   LIMIT $1""",
                limit,
            )
        return [self._row_to_item(r) for r in rows]

    async def list_history(self, limit: int = 50) -> list[HumanReviewItem]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM human_review_queue
                   WHERE status IN ('approved', 'rejected')
                   ORDER BY reviewed_at DESC
                   LIMIT $1""",
                limit,
            )
        return [self._row_to_item(r) for r in rows]

    async def approve(self, review_id: str, reviewer: str = "admin", comment: str | None = None) -> HumanReviewItem | None:
        return await self._decide(review_id, "approved", reviewer, comment)

    async def reject(self, review_id: str, reviewer: str = "admin", comment: str | None = None) -> HumanReviewItem | None:
        return await self._decide(review_id, "rejected", reviewer, comment)

    async def get_review(self, review_id: str) -> HumanReviewItem | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM human_review_queue WHERE id = $1", review_id)
        return self._row_to_item(row) if row else None

    async def _decide(self, review_id: str, status: str, reviewer: str, comment: str | None) -> HumanReviewItem | None:
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE human_review_queue
                   SET status = $2, reviewer = $3, comment = $4, reviewed_at = $5
                   WHERE id = $1 AND status = 'pending'
                   RETURNING *""",
                review_id, status, reviewer, comment, now,
            )
        if row:
            logger.info("review_decided", id=review_id, status=status, reviewer=reviewer)
            return self._row_to_item(row)
        return None

    @staticmethod
    def _row_to_item(row) -> HumanReviewItem:
        meta = None
        if row["metadata_json"]:
            try:
                meta = json.loads(row["metadata_json"])
            except (json.JSONDecodeError, TypeError):
                meta = None
        return HumanReviewItem(
            id=row["id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            reviewer=row["reviewer"],
            comment=row["comment"],
            metadata_json=meta,
            created_at=str(row["created_at"]) if row["created_at"] else "",
            reviewed_at=str(row["reviewed_at"]) if row["reviewed_at"] else None,
        )
