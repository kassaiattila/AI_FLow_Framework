"""
@test_registry:
    suite: service-unit
    component: services.service_manager
    covers: [src/aiflow/services/service_manager/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, service-manager, lifecycle, metrics, sqlalchemy]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.service_manager.service import (
    ServiceManagerConfig,
    ServiceManagerService,
)


def _make_metrics_row():
    """Mock SQLAlchemy result row for service_metrics aggregation."""
    return (
        100,  # calls
        90,  # ok
        10,  # errs
        45.5,  # avg_ms
        5,  # min_ms
        200,  # max_ms
        0.25,  # cost
    )


@pytest.fixture()
def mock_session_factory():
    """Mock SQLAlchemy async session factory."""
    session = AsyncMock()
    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory, session


@pytest.fixture()
def svc(mock_session_factory) -> ServiceManagerService:
    factory, _session = mock_session_factory
    return ServiceManagerService(session_factory=factory, config=ServiceManagerConfig())


class TestServiceManagerService:
    @pytest.mark.asyncio
    async def test_list_services(self, svc: ServiceManagerService) -> None:
        """list_services returns ServiceSummary list."""
        services = await svc.list_services()
        assert isinstance(services, list)
        assert len(services) > 0
        names = {s.name for s in services}
        assert "email_connector" in names
        assert "classifier" in names

    @pytest.mark.asyncio
    async def test_get_service_detail(
        self, svc: ServiceManagerService, mock_session_factory
    ) -> None:
        """get_service_detail returns ServiceDetail for a named service."""
        _factory, session = mock_session_factory
        # Mock pipeline query
        result = MagicMock()
        result.fetchall.return_value = [("pipeline-1",)]
        session.execute = AsyncMock(return_value=result)

        detail = await svc.get_service_detail("email_connector")
        assert detail.name == "email_connector"
        assert detail.status == "available"

    @pytest.mark.asyncio
    async def test_restart_service(self, svc: ServiceManagerService) -> None:
        """restart_service returns False for non-registered service."""
        # Without a running ServiceRegistry, restart should return False
        result = await svc.restart_service("nonexistent_service")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_service_metrics(
        self, svc: ServiceManagerService, mock_session_factory
    ) -> None:
        """get_service_metrics returns ServiceMetrics with aggregated values."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchone.return_value = _make_metrics_row()
        session.execute = AsyncMock(return_value=result)

        metrics = await svc.get_service_metrics("classifier", period="24h")
        assert metrics.service_name == "classifier"
        assert metrics.call_count == 100
        assert metrics.success_count == 90
        assert metrics.error_count == 10
        assert metrics.avg_duration_ms == 45.5

    @pytest.mark.asyncio
    async def test_record_metric(self, svc: ServiceManagerService, mock_session_factory) -> None:
        """record_metric executes without error."""
        _factory, session = mock_session_factory
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        # Should not raise
        await svc.record_metric("classifier", duration_ms=50, success=True, cost=0.01)
        assert session.execute.called
