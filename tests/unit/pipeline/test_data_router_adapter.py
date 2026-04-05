"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.data_router
    covers: [src/aiflow/pipeline/adapters/data_router_adapter.py]
    phase: C8
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [pipeline, adapter, data-router]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapters.data_router_adapter import (
    DataRouterFilterAdapter,
    DataRouterRouteAdapter,
    FilterInput,
    FilterOutput,
    RouteFilesInput,
    RouteFilesOutput,
)


# --- Fake service ---


@dataclass
class FakeFilterResult:
    filtered_items: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    matched: int = 0


@dataclass
class FakeRoutedFile:
    file_path: str = ""
    target_path: str | None = None
    rule_matched: str | None = None
    action: str = ""
    success: bool = True
    error: str | None = None


class FakeDataRouterService:
    def __init__(self) -> None:
        self.last_filter_call: dict[str, Any] = {}
        self.last_route_call: dict[str, Any] = {}

    async def filter(self, items, condition):
        self.last_filter_call = {"items": items, "condition": condition}
        matched = [i for i in items if i.get("keep")]
        return FakeFilterResult(
            filtered_items=matched,
            total=len(items),
            matched=len(matched),
        )

    async def route_files(self, files, rules):
        self.last_route_call = {"files": files, "rules": rules}
        return [
            FakeRoutedFile(file_path=f.get("file_path", ""), action="tag", success=True)
            for f in files
        ]


@pytest.fixture()
def ctx() -> ExecutionContext:
    return ExecutionContext()


@pytest.fixture()
def fake_svc() -> FakeDataRouterService:
    return FakeDataRouterService()


# ---------------------------------------------------------------------------
# Filter adapter tests
# ---------------------------------------------------------------------------


class TestFilterAdapter:
    @pytest.mark.asyncio
    async def test_basic_filter(
        self, fake_svc: FakeDataRouterService, ctx: ExecutionContext
    ) -> None:
        adapter = DataRouterFilterAdapter(service=fake_svc)
        result = await adapter.execute(
            input_data={
                "items": [{"keep": True}, {"keep": False}],
                "condition": "{{ keep }}",
            },
            config={},
            ctx=ctx,
        )
        assert result["total"] == 2
        assert result["matched"] == 1
        assert fake_svc.last_filter_call["condition"] == "{{ keep }}"

    @pytest.mark.asyncio
    async def test_config_overrides(
        self, fake_svc: FakeDataRouterService, ctx: ExecutionContext
    ) -> None:
        adapter = DataRouterFilterAdapter(service=fake_svc)
        await adapter.execute(
            input_data={"items": [{"x": 1}], "condition": "orig"},
            config={"condition": "override"},
            ctx=ctx,
        )
        assert fake_svc.last_filter_call["condition"] == "override"

    def test_adapter_registered(self) -> None:
        from aiflow.pipeline.adapter_base import adapter_registry

        a = adapter_registry.get("data_router", "filter")
        assert a.service_name == "data_router"
        assert a.method_name == "filter"

    def test_input_schema(self) -> None:
        inp = FilterInput(items=[{"a": 1}], condition="{{ a > 0 }}")
        assert len(inp.items) == 1

    def test_output_schema(self) -> None:
        out = FilterOutput(filtered_items=[], total=5, matched=2)
        assert out.total == 5


# ---------------------------------------------------------------------------
# Route adapter tests
# ---------------------------------------------------------------------------


class TestRouteAdapter:
    @pytest.mark.asyncio
    async def test_basic_route(
        self, fake_svc: FakeDataRouterService, ctx: ExecutionContext
    ) -> None:
        adapter = DataRouterRouteAdapter(service=fake_svc)
        result = await adapter.execute(
            input_data={
                "files": [{"file_path": "/tmp/a.pdf"}],
                "rules": [{"condition": "{{ true }}", "action": "tag"}],
            },
            config={},
            ctx=ctx,
        )
        assert result["total"] == 1
        assert result["success_count"] == 1
        assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_config_overrides_rules(
        self, fake_svc: FakeDataRouterService, ctx: ExecutionContext
    ) -> None:
        adapter = DataRouterRouteAdapter(service=fake_svc)
        await adapter.execute(
            input_data={"files": [{"file_path": "x"}], "rules": []},
            config={
                "rules": [{"condition": "{{ true }}", "action": "notify"}],
            },
            ctx=ctx,
        )
        assert len(fake_svc.last_route_call["rules"]) == 1

    @pytest.mark.asyncio
    async def test_empty_files(
        self, fake_svc: FakeDataRouterService, ctx: ExecutionContext
    ) -> None:
        adapter = DataRouterRouteAdapter(service=fake_svc)
        result = await adapter.execute(
            input_data={"files": [], "rules": []},
            config={},
            ctx=ctx,
        )
        assert result["total"] == 0

    def test_route_adapter_registered(self) -> None:
        from aiflow.pipeline.adapter_base import adapter_registry

        a = adapter_registry.get("data_router", "route_files")
        assert a.service_name == "data_router"
        assert a.method_name == "route_files"

    def test_route_input_schema(self) -> None:
        inp = RouteFilesInput(
            files=[{"file_path": "/tmp/a.pdf"}],
            rules=[{"condition": "{{ true }}", "action": "tag"}],
        )
        assert len(inp.files) == 1

    def test_route_output_schema(self) -> None:
        out = RouteFilesOutput(
            routed_files=[], total=3, success_count=2, failed_count=1
        )
        assert out.failed_count == 1
