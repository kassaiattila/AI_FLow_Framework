"""
@test_registry:
    suite: service-unit
    component: services.service_manager
    covers: [
        src/aiflow/services/service_manager/service.py,
        src/aiflow/pipeline/adapters/service_manager_adapter.py,
    ]
    phase: C10
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [service, service-manager, metrics, adapter]
"""

from __future__ import annotations

import pytest

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapters.service_manager_adapter import (
    ServiceDetailInput,
    ServiceDetailOutput,
    ServiceManagerDetailAdapter,
)
from aiflow.services.service_manager.service import (
    ServiceDetail,
    ServiceManagerConfig,
    ServiceManagerService,
    ServiceMetrics,
    ServiceSummary,
)


@pytest.fixture()
def svc() -> ServiceManagerService:
    return ServiceManagerService(session_factory=None, config=ServiceManagerConfig())


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestModels:
    def test_service_summary(self) -> None:
        s = ServiceSummary(name="cache", status="running", has_adapter=True)
        assert s.name == "cache"
        assert s.has_adapter is True

    def test_service_detail(self) -> None:
        d = ServiceDetail(
            name="classifier",
            status="available",
            adapter_methods=["classify"],
            pipelines_using=["invoice_v1"],
        )
        assert d.adapter_methods == ["classify"]
        assert len(d.pipelines_using) == 1

    def test_service_metrics_defaults(self) -> None:
        m = ServiceMetrics(service_name="test")
        assert m.call_count == 0
        assert m.error_rate == 0.0
        assert m.total_cost == 0.0

    def test_config(self) -> None:
        cfg = ServiceManagerConfig()
        assert cfg.enabled is True


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_service_name(self, svc: ServiceManagerService) -> None:
        assert svc.service_name == "service_manager"

    def test_description(self, svc: ServiceManagerService) -> None:
        assert "management" in svc.service_description.lower()

    @pytest.mark.asyncio
    async def test_start_stop(self, svc: ServiceManagerService) -> None:
        await svc.start()
        assert svc.status.value == "running"
        await svc.stop()
        assert svc.status.value == "stopped"

    @pytest.mark.asyncio
    async def test_health_check(self, svc: ServiceManagerService) -> None:
        assert await svc.health_check() is True


# ---------------------------------------------------------------------------
# List services
# ---------------------------------------------------------------------------


class TestListServices:
    @pytest.mark.asyncio
    async def test_list_returns_known_services(self, svc: ServiceManagerService) -> None:
        await svc.start()
        items = await svc.list_services()
        assert len(items) >= 10  # at least known services
        names = [s.name for s in items]
        assert "email_connector" in names
        assert "classifier" in names
        assert "notification" in names
        assert "data_router" in names

    @pytest.mark.asyncio
    async def test_list_has_adapter_flag(self, svc: ServiceManagerService) -> None:
        await svc.start()
        items = await svc.list_services()
        by_name = {s.name: s for s in items}
        # email_connector has a registered adapter
        assert by_name["email_connector"].has_adapter is True
        # cache does not have a pipeline adapter
        assert by_name["cache"].has_adapter is False


# ---------------------------------------------------------------------------
# Service detail
# ---------------------------------------------------------------------------


class TestServiceDetail:
    @pytest.mark.asyncio
    async def test_detail_with_adapter(self, svc: ServiceManagerService) -> None:
        await svc.start()
        detail = await svc.get_service_detail("notification")
        assert detail.name == "notification"
        assert detail.has_adapter is True
        assert "send" in detail.adapter_methods

    @pytest.mark.asyncio
    async def test_detail_without_adapter(self, svc: ServiceManagerService) -> None:
        await svc.start()
        detail = await svc.get_service_detail("cache")
        assert detail.has_adapter is False
        assert detail.adapter_methods == []

    @pytest.mark.asyncio
    async def test_detail_unknown_service(self, svc: ServiceManagerService) -> None:
        await svc.start()
        detail = await svc.get_service_detail("nonexistent")
        assert detail.name == "nonexistent"
        assert detail.has_adapter is False

    @pytest.mark.asyncio
    async def test_detail_pipelines_empty_no_db(self, svc: ServiceManagerService) -> None:
        await svc.start()
        detail = await svc.get_service_detail("email_connector")
        assert detail.pipelines_using == []  # no DB, so empty


# ---------------------------------------------------------------------------
# Metrics (no DB)
# ---------------------------------------------------------------------------


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_no_db_returns_empty(self, svc: ServiceManagerService) -> None:
        metrics = await svc.get_service_metrics("classifier", "24h")
        assert metrics.service_name == "classifier"
        assert metrics.call_count == 0

    def test_period_to_timedelta(self) -> None:
        from datetime import timedelta

        assert ServiceManagerService._period_to_timedelta("1h") == timedelta(hours=1)
        assert ServiceManagerService._period_to_timedelta("7d") == timedelta(days=7)
        assert ServiceManagerService._period_to_timedelta("unknown") == timedelta(hours=24)

    @pytest.mark.asyncio
    async def test_record_metric_no_db(self, svc: ServiceManagerService) -> None:
        # Should not raise
        await svc.record_metric("test", 100, True, 0.01)


# ---------------------------------------------------------------------------
# Restart (no registry in unit test)
# ---------------------------------------------------------------------------


class TestRestart:
    @pytest.mark.asyncio
    async def test_restart_unknown_returns_false(self, svc: ServiceManagerService) -> None:
        await svc.start()
        # Will fail because _get_registry creates infra services needing Redis
        result = await svc.restart_service("nonexistent_service_xyz")
        assert result is False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class TestServiceManagerAdapter:
    @pytest.mark.asyncio
    async def test_adapter_basic(self) -> None:
        adapter = ServiceManagerDetailAdapter(
            service=ServiceManagerService(config=ServiceManagerConfig())
        )
        await adapter._service.start()  # type: ignore[union-attr]
        result = await adapter.execute(
            input_data={"name": "email_connector"},
            config={},
            ctx=ExecutionContext(),
        )
        assert result["name"] == "email_connector"
        assert result["has_adapter"] is True

    @pytest.mark.asyncio
    async def test_adapter_config_override(self) -> None:
        adapter = ServiceManagerDetailAdapter(
            service=ServiceManagerService(config=ServiceManagerConfig())
        )
        await adapter._service.start()  # type: ignore[union-attr]
        result = await adapter.execute(
            input_data={"name": "ignored"},
            config={"name": "notification"},
            ctx=ExecutionContext(),
        )
        assert result["name"] == "notification"

    def test_adapter_registered(self) -> None:
        from aiflow.pipeline.adapter_base import adapter_registry

        a = adapter_registry.get("service_manager", "get_service_detail")
        assert a.service_name == "service_manager"

    def test_input_schema(self) -> None:
        inp = ServiceDetailInput(name="test")
        assert inp.name == "test"

    def test_output_schema(self) -> None:
        out = ServiceDetailOutput(name="x", status="ok", has_adapter=True)
        assert out.has_adapter is True
