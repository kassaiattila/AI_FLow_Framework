"""
@test_registry:
    suite: service-unit
    component: services.data_router
    covers: [src/aiflow/services/data_router/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, data-router, filter, routing, jinja2]
"""

from __future__ import annotations

import pytest

from aiflow.services.data_router.service import (
    DataRouterConfig,
    DataRouterService,
    RoutingRule,
)


@pytest.fixture()
def svc() -> DataRouterService:
    return DataRouterService(config=DataRouterConfig())


class TestDataRouterService:
    @pytest.mark.asyncio
    async def test_filter_matching_items(self, svc: DataRouterService) -> None:
        """filter with matching condition returns correct FilterResult."""
        items = [
            {"name": "big", "total_amount": 200_000},
            {"name": "small", "total_amount": 50_000},
            {"name": "huge", "total_amount": 500_000},
        ]
        result = await svc.filter(items, "total_amount > 100000")
        assert result.matched == 2
        assert result.total == 3
        assert len(result.filtered_items) == 2
        names = {i["name"] for i in result.filtered_items}
        assert names == {"big", "huge"}

    @pytest.mark.asyncio
    async def test_filter_no_match(self, svc: DataRouterService) -> None:
        """filter with non-matching condition returns empty list."""
        items = [
            {"name": "a", "value": 10},
            {"name": "b", "value": 20},
        ]
        result = await svc.filter(items, "value > 1000")
        assert result.matched == 0
        assert result.total == 2
        assert result.filtered_items == []

    @pytest.mark.asyncio
    async def test_route_files_by_rules(self, svc: DataRouterService) -> None:
        """route_files applies first matching rule to each file."""
        files = [
            {"file_path": "/tmp/invoice.pdf", "doc_type": "invoice"},
            {"file_path": "/tmp/report.pdf", "doc_type": "report"},
        ]
        rules = [
            RoutingRule(
                condition="doc_type == 'invoice'",
                action="tag",
                config={},
            ),
            RoutingRule(
                condition="doc_type == 'report'",
                action="notify",
                config={},
            ),
        ]
        results = await svc.route_files(files, rules)
        assert len(results) == 2
        assert results[0].action == "tag"
        assert results[0].rule_matched == "doc_type == 'invoice'"
        assert results[1].action == "notify"

    @pytest.mark.asyncio
    async def test_move_to_dir_template(self, svc: DataRouterService) -> None:
        """move_to_dir with non-existent source returns success=False."""
        result = await svc.move_to_dir(
            "/nonexistent/file.pdf",
            "archive/{{ vendor_id }}/{{ year }}",
            {"vendor_id": "V001", "year": "2024"},
        )
        assert result.success is False
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_health_check(self, svc: DataRouterService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
