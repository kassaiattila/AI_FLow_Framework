"""
@test_registry:
    suite: service-unit
    component: services.human_review
    covers: [src/aiflow/services/human_review/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, human-review, postgresql, sla, escalation]
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from aiflow.services.human_review.service import HumanReviewItem, HumanReviewService


def _make_row(
    status: str = "pending",
    priority: str = "normal",
    reviewer: str | None = None,
    comment: str | None = None,
    metadata_json: str | None = None,
    reviewed_at=None,
) -> dict:
    return {
        "id": "rev-001",
        "entity_type": "document",
        "entity_id": "doc-42",
        "title": "Review extracted invoice",
        "description": "Please verify amounts",
        "status": status,
        "priority": priority,
        "reviewer": reviewer,
        "comment": comment,
        "metadata_json": metadata_json,
        "created_at": datetime.now(UTC),
        "reviewed_at": reviewed_at,
    }


@pytest.fixture()
def svc(mock_pool) -> HumanReviewService:
    pool, _conn = mock_pool
    service = HumanReviewService()
    service._pool = pool
    return service


class TestHumanReviewService:
    @pytest.mark.asyncio
    async def test_create_review(self, svc: HumanReviewService, mock_pool) -> None:
        """create_review returns a pending HumanReviewItem."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=_make_row())

        item = await svc.create_review(
            entity_type="document",
            entity_id="doc-42",
            title="Review extracted invoice",
        )
        assert isinstance(item, HumanReviewItem)
        assert item.status == "pending"
        assert item.entity_type == "document"

    @pytest.mark.asyncio
    async def test_approve_review(self, svc: HumanReviewService, mock_pool) -> None:
        """approve sets status=approved and reviewer."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(
            return_value=_make_row(
                status="approved",
                reviewer="admin",
                reviewed_at=datetime.now(UTC),
            )
        )

        item = await svc.approve("rev-001", reviewer="admin")
        assert item is not None
        assert item.status == "approved"
        assert item.reviewer == "admin"

    @pytest.mark.asyncio
    async def test_reject_review(self, svc: HumanReviewService, mock_pool) -> None:
        """reject sets status=rejected."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(
            return_value=_make_row(
                status="rejected",
                reviewer="admin",
                comment="incorrect data",
                reviewed_at=datetime.now(UTC),
            )
        )

        item = await svc.reject("rev-001", reviewer="admin", comment="incorrect data")
        assert item is not None
        assert item.status == "rejected"
        assert item.comment == "incorrect data"

    @pytest.mark.asyncio
    async def test_list_pending_priority_order(self, svc: HumanReviewService, mock_pool) -> None:
        """list_pending returns items ordered by priority."""
        _pool, conn = mock_pool
        rows = [
            _make_row(priority="critical"),
            _make_row(priority="high"),
            _make_row(priority="normal"),
        ]
        conn.fetch = AsyncMock(return_value=rows)

        items = await svc.list_pending()
        assert len(items) == 3
        # DB query orders by priority, so first item should be critical
        assert items[0].priority == "critical"
        assert items[1].priority == "high"

    @pytest.mark.asyncio
    async def test_check_sla_deadlines(self, svc: HumanReviewService, mock_pool) -> None:
        """check_sla_deadlines returns overdue pending reviews."""
        _pool, conn = mock_pool
        overdue_rows = [_make_row(), _make_row()]
        conn.fetch = AsyncMock(return_value=overdue_rows)

        overdue = await svc.check_sla_deadlines(sla_hours=24.0)
        assert len(overdue) == 2
        conn.fetch.assert_awaited_once()
