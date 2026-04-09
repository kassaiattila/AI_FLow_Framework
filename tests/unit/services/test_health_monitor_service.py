"""
@test_registry:
    suite: service-unit
    component: services.health_monitor
    covers: [src/aiflow/services/health_monitor/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [service, health-monitor, postgresql, redis]
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from aiflow.services.health_monitor.service import (
    HealthMonitorService,
    ServiceHealth,
)


@pytest.fixture()
def svc(mock_pool) -> HealthMonitorService:
    pool, _conn = mock_pool
    service = HealthMonitorService()
    service._pool = pool
    return service


class TestHealthMonitorService:
    @pytest.mark.asyncio
    async def test_check_all_returns_list(self, svc: HealthMonitorService, mock_pool) -> None:
        """check_all returns a list of ServiceHealth objects."""
        _pool, conn = mock_pool
        conn.fetchval = AsyncMock(return_value=1)
        conn.execute = AsyncMock()

        # Patch Redis check to avoid real connection (lazy import inside _check_redis)
        with patch("redis.asyncio.from_url") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.aclose = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            results = await svc.check_all()

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, ServiceHealth) for r in results)

    @pytest.mark.asyncio
    async def test_get_service_health(self, svc: HealthMonitorService, mock_pool) -> None:
        """get_service_health returns ServiceHealth for existing service."""
        _pool, conn = mock_pool
        now = datetime.now(UTC)
        conn.fetchrow = AsyncMock(
            return_value={
                "service_name": "postgresql",
                "status": "healthy",
                "latency_ms": 2.5,
                "details": {"version": "16"},
                "checked_at": now,
            }
        )

        result = await svc.get_service_health("postgresql")
        assert result is not None
        assert result.service_name == "postgresql"
        assert result.status == "healthy"
        assert result.latency_ms == 2.5

    @pytest.mark.asyncio
    async def test_get_metrics_aggregation(self, svc: HealthMonitorService, mock_pool) -> None:
        """get_metrics returns aggregated metrics per service."""
        _pool, conn = mock_pool
        conn.fetch = AsyncMock(
            return_value=[
                {
                    "service_name": "postgresql",
                    "check_count": 100,
                    "avg_latency_ms": 3.5,
                    "p95_latency_ms": 8.2,
                    "success_rate": 0.98,
                },
            ]
        )

        metrics = await svc.get_metrics()
        assert len(metrics) == 1
        assert metrics[0]["service_name"] == "postgresql"
        assert metrics[0]["avg_latency_ms"] == 3.5
        assert metrics[0]["p95_latency_ms"] == 8.2
        assert metrics[0]["success_rate"] == 98.0

    @pytest.mark.asyncio
    async def test_unknown_service_returns_none(self, svc: HealthMonitorService, mock_pool) -> None:
        """get_service_health returns None for unknown service."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=None)

        result = await svc.get_service_health("nonexistent_service")
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_logging(self, svc: HealthMonitorService, mock_pool) -> None:
        """_persist_check writes health check to DB."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock()

        health = ServiceHealth(
            service_name="test",
            status="healthy",
            latency_ms=1.0,
            details={"key": "value"},
            checked_at=datetime.now(UTC).isoformat(),
        )
        await svc._persist_check(health)
        conn.execute.assert_awaited_once()
