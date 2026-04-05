"""
@test_registry:
    suite: api-unit
    component: api.human_review.sla
    covers: [src/aiflow/services/human_review/service.py, src/aiflow/api/v1/human_review.py]
    phase: S12
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [sla, escalation, human-review]
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiflow.services.human_review.service import HumanReviewItem, HumanReviewService


def _make_pool_mock(conn_mock: AsyncMock) -> MagicMock:
    """Create a pool mock with proper async context manager for acquire()."""
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield conn_mock

    pool.acquire = _acquire
    return pool


class TestHumanReviewSLA:
    """Tests for SLA escalation in HumanReviewService."""

    @pytest.fixture
    def svc(self):
        return HumanReviewService(db_url="postgresql://test:test@localhost/test")

    def test_review_item_model(self):
        """HumanReviewItem can carry escalation metadata."""
        item = HumanReviewItem(
            id="r1",
            entity_type="document",
            entity_id="d1",
            title="Review invoice",
            metadata_json={
                "escalated_at": "2026-04-04T12:00:00",
                "escalation_reason": "SLA exceeded",
            },
        )
        assert item.metadata_json["escalated_at"] is not None
        assert "SLA" in item.metadata_json["escalation_reason"]

    def test_review_item_no_metadata(self):
        """HumanReviewItem works without metadata."""
        item = HumanReviewItem(
            id="r2",
            entity_type="email",
            entity_id="e1",
            title="Review classification",
        )
        assert item.metadata_json is None
        assert item.status == "pending"

    @pytest.mark.asyncio
    async def test_escalate_not_found(self, svc):
        """Escalate returns None for non-existent review."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        svc._pool = _make_pool_mock(mock_conn)

        result = await svc.escalate("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_sla_deadlines_empty(self, svc):
        """No overdue reviews returns empty list."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        svc._pool = _make_pool_mock(mock_conn)

        result = await svc.check_sla_deadlines(sla_hours=24.0)
        assert result == []

    @pytest.mark.asyncio
    async def test_check_and_escalate_skips_already_escalated(self, svc):
        """Already-escalated reviews are skipped."""
        already_escalated = HumanReviewItem(
            id="r3",
            entity_type="doc",
            entity_id="d3",
            title="Old review",
            metadata_json={"escalated_at": "2026-04-03T10:00:00"},
        )

        with (
            patch.object(
                svc,
                "check_sla_deadlines",
                new_callable=AsyncMock,
                return_value=[already_escalated],
            ),
            patch.object(svc, "escalate", new_callable=AsyncMock) as mock_esc,
            patch.object(
                svc,
                "_send_escalation_notifications",
                new_callable=AsyncMock,
            ),
        ):
            result = await svc.check_and_escalate(sla_hours=24.0)

        assert result == []
        mock_esc.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_escalate_escalates_new(self, svc):
        """New overdue reviews get escalated."""
        overdue = HumanReviewItem(
            id="r4",
            entity_type="doc",
            entity_id="d4",
            title="Overdue review",
            metadata_json=None,
        )
        escalated = HumanReviewItem(
            id="r4",
            entity_type="doc",
            entity_id="d4",
            title="Overdue review",
            priority="high",
            metadata_json={"escalated_at": "2026-04-04T14:00:00"},
        )

        with (
            patch.object(
                svc,
                "check_sla_deadlines",
                new_callable=AsyncMock,
                return_value=[overdue],
            ),
            patch.object(
                svc,
                "escalate",
                new_callable=AsyncMock,
                return_value=escalated,
            ),
            patch.object(
                svc,
                "_send_escalation_notifications",
                new_callable=AsyncMock,
            ),
        ):
            result = await svc.check_and_escalate(sla_hours=24.0)

        assert len(result) == 1
        assert result[0].priority == "high"
