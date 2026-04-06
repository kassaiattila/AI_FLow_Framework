"""
@test_registry:
    suite: service-unit
    component: services.rpa_browser
    covers: [src/aiflow/services/rpa_browser/service.py]
    phase: B2.1
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, rpa, browser, yaml, postgresql]
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from aiflow.services.rpa_browser.service import (
    RPABrowserConfig,
    RPABrowserService,
    RPAConfigRecord,
    RPAExecutionRecord,
)

SAMPLE_YAML = """
steps:
  - name: open_page
    action: navigate
    url: https://example.com
  - name: click_button
    action: click
    selector: "#submit"
"""


def _make_config_row(name: str = "test-rpa") -> dict:
    now = datetime.now(UTC)
    return {
        "id": "cfg-001",
        "name": name,
        "description": "Test RPA config",
        "yaml_config": SAMPLE_YAML,
        "target_url": "https://example.com",
        "is_active": True,
        "schedule_cron": None,
        "created_at": now,
        "updated_at": now,
    }


def _make_exec_row(status: str = "completed") -> dict:
    now = datetime.now(UTC)
    return {
        "id": "exec-001",
        "config_id": "cfg-001",
        "status": status,
        "steps_total": 2,
        "steps_completed": 2,
        "results": '{"steps": []}',
        "screenshots": "[]",
        "error": None,
        "duration_ms": 150.0,
        "started_at": now,
        "completed_at": now,
    }


@pytest.fixture()
def svc(mock_pool) -> RPABrowserService:
    pool, _conn = mock_pool
    service = RPABrowserService(config=RPABrowserConfig())
    service._pool = pool
    return service


class TestRPABrowserService:
    @pytest.mark.asyncio
    async def test_create_config(self, svc: RPABrowserService, mock_pool) -> None:
        """create_config persists and returns RPAConfigRecord."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="INSERT 0 1")

        record = await svc.create_config(
            name="test-rpa",
            yaml_config=SAMPLE_YAML,
            description="Test",
            target_url="https://example.com",
        )
        assert isinstance(record, RPAConfigRecord)
        assert record.name == "test-rpa"
        assert record.yaml_config == SAMPLE_YAML

    @pytest.mark.asyncio
    async def test_list_configs(self, svc: RPABrowserService, mock_pool) -> None:
        """list_configs returns list of RPAConfigRecord."""
        _pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[_make_config_row(), _make_config_row("rpa-2")])

        configs = await svc.list_configs()
        assert len(configs) == 2
        assert all(isinstance(c, RPAConfigRecord) for c in configs)

    @pytest.mark.asyncio
    async def test_get_config(self, svc: RPABrowserService, mock_pool) -> None:
        """get_config returns RPAConfigRecord for existing ID."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=_make_config_row())

        record = await svc.get_config("cfg-001")
        assert record is not None
        assert record.id == "cfg-001"

    @pytest.mark.asyncio
    async def test_execute_logs_result(self, svc: RPABrowserService, mock_pool) -> None:
        """execute runs steps and returns RPAExecutionRecord."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=_make_config_row())
        conn.execute = AsyncMock(return_value="INSERT 0 1")

        record = await svc.execute("cfg-001")
        assert isinstance(record, RPAExecutionRecord)
        assert record.status == "completed"
        assert record.steps_total == 2
        assert record.steps_completed == 2

    @pytest.mark.asyncio
    async def test_delete_config(self, svc: RPABrowserService, mock_pool) -> None:
        """delete_config returns True when row is deleted."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="DELETE 1")

        result = await svc.delete_config("cfg-001")
        assert result is True
