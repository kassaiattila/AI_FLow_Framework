"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapter_base
    covers: [src/aiflow/pipeline/adapter_base.py]
    phase: C1
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [pipeline, adapter, registry]
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import (
    AdapterRegistry,
    BaseAdapter,
    ServiceAdapter,
)

# --- Test fixtures ---


class DummyInput(BaseModel):
    text: str = "hello"
    count: int = 1


class DummyOutput(BaseModel):
    result: str = ""
    length: int = 0


class DummyAdapter(BaseAdapter):
    service_name = "test_service"
    method_name = "test_method"
    input_schema = DummyInput
    output_schema = DummyOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        data = (
            input_data
            if isinstance(input_data, DummyInput)
            else DummyInput.model_validate(input_data)
        )
        return {
            "result": data.text * data.count,
            "length": len(data.text) * data.count,
        }


class FailingAdapter(BaseAdapter):
    service_name = "failing_service"
    method_name = "fail"
    input_schema = DummyInput
    output_schema = DummyOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        raise RuntimeError("intentional failure")


class AnotherAdapter(BaseAdapter):
    service_name = "test_service"
    method_name = "another_method"
    input_schema = DummyInput
    output_schema = DummyOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        return {"result": "another", "length": 7}


# --- Protocol compliance ---


class TestServiceAdapterProtocol:
    def test_base_adapter_is_service_adapter(self):
        adapter = DummyAdapter()
        assert isinstance(adapter, ServiceAdapter)

    def test_adapter_has_required_attributes(self):
        adapter = DummyAdapter()
        assert adapter.service_name == "test_service"
        assert adapter.method_name == "test_method"
        assert adapter.input_schema is DummyInput
        assert adapter.output_schema is DummyOutput


# --- BaseAdapter.execute ---


class TestBaseAdapterExecute:
    @pytest.mark.asyncio
    async def test_execute_validates_input_and_returns_dict(self):
        adapter = DummyAdapter()
        ctx = ExecutionContext()
        result = await adapter.execute({"text": "abc", "count": 3}, {}, ctx)
        assert result == {"result": "abcabcabc", "length": 9}

    @pytest.mark.asyncio
    async def test_execute_with_defaults(self):
        adapter = DummyAdapter()
        ctx = ExecutionContext()
        result = await adapter.execute({}, {}, ctx)
        assert result == {"result": "hello", "length": 5}

    @pytest.mark.asyncio
    async def test_execute_rejects_invalid_input(self):
        adapter = DummyAdapter()
        ctx = ExecutionContext()
        with pytest.raises(Exception):  # ValidationError
            await adapter.execute({"count": "not_a_number"}, {}, ctx)

    @pytest.mark.asyncio
    async def test_execute_propagates_runtime_error(self):
        adapter = FailingAdapter()
        ctx = ExecutionContext()
        with pytest.raises(RuntimeError, match="intentional failure"):
            await adapter.execute({"text": "x"}, {}, ctx)


# --- BaseAdapter.execute_for_each ---


class TestBaseAdapterForEach:
    @pytest.mark.asyncio
    async def test_for_each_processes_all_items(self):
        adapter = DummyAdapter()
        ctx = ExecutionContext()
        items = [
            {"text": "a", "count": 1},
            {"text": "bb", "count": 2},
            {"text": "ccc", "count": 3},
        ]
        results = await adapter.execute_for_each(items, {}, ctx, concurrency=2)
        assert len(results) == 3
        assert results[0] == {"result": "a", "length": 1}
        assert results[1] == {"result": "bbbb", "length": 4}
        assert results[2] == {"result": "ccccccccc", "length": 9}

    @pytest.mark.asyncio
    async def test_for_each_empty_list(self):
        adapter = DummyAdapter()
        ctx = ExecutionContext()
        results = await adapter.execute_for_each([], {}, ctx)
        assert results == []

    @pytest.mark.asyncio
    async def test_for_each_failure_propagates(self):
        adapter = FailingAdapter()
        ctx = ExecutionContext()
        with pytest.raises(RuntimeError):
            await adapter.execute_for_each([{"text": "x"}], {}, ctx)


# --- AdapterRegistry ---


class TestAdapterRegistry:
    def test_register_and_get(self):
        registry = AdapterRegistry()
        adapter = DummyAdapter()
        registry.register(adapter)
        assert registry.get("test_service", "test_method") is adapter

    def test_register_duplicate_raises(self):
        registry = AdapterRegistry()
        registry.register(DummyAdapter())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummyAdapter())

    def test_get_missing_raises(self):
        registry = AdapterRegistry()
        with pytest.raises(KeyError, match="No adapter"):
            registry.get("nonexistent", "method")

    def test_get_or_none(self):
        registry = AdapterRegistry()
        assert registry.get_or_none("x", "y") is None
        adapter = DummyAdapter()
        registry.register(adapter)
        assert registry.get_or_none("test_service", "test_method") is adapter

    def test_has(self):
        registry = AdapterRegistry()
        assert not registry.has("test_service", "test_method")
        registry.register(DummyAdapter())
        assert registry.has("test_service", "test_method")

    def test_unregister(self):
        registry = AdapterRegistry()
        registry.register(DummyAdapter())
        registry.unregister("test_service", "test_method")
        assert not registry.has("test_service", "test_method")

    def test_unregister_missing_raises(self):
        registry = AdapterRegistry()
        with pytest.raises(KeyError):
            registry.unregister("x", "y")

    def test_list_adapters(self):
        registry = AdapterRegistry()
        registry.register(DummyAdapter())
        registry.register(AnotherAdapter())
        adapters = registry.list_adapters()
        assert ("test_service", "test_method") in adapters
        assert ("test_service", "another_method") in adapters
        assert len(adapters) == 2

    def test_len_and_contains(self):
        registry = AdapterRegistry()
        assert len(registry) == 0
        registry.register(DummyAdapter())
        assert len(registry) == 1
        assert ("test_service", "test_method") in registry
        assert ("x", "y") not in registry

    def test_multiple_methods_same_service(self):
        """Same service can have multiple method adapters."""
        registry = AdapterRegistry()
        registry.register(DummyAdapter())
        registry.register(AnotherAdapter())
        assert registry.get("test_service", "test_method") is not None
        assert registry.get("test_service", "another_method") is not None

    def test_repr(self):
        registry = AdapterRegistry()
        registry.register(DummyAdapter())
        assert "test_service" in repr(registry)


# --- BaseAdapter repr ---


class TestBaseAdapterRepr:
    def test_repr(self):
        adapter = DummyAdapter()
        assert "DummyAdapter" in repr(adapter)
        assert "test_service.test_method" in repr(adapter)
