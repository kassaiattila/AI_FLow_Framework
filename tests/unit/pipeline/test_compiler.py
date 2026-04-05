"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.compiler
    covers: [src/aiflow/pipeline/compiler.py]
    phase: C2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [pipeline, compiler, dag]
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import AdapterRegistry, BaseAdapter
from aiflow.pipeline.compiler import PipelineCompileError, PipelineCompiler
from aiflow.pipeline.schema import PipelineDefinition


# --- Test fixtures ---


class StubInput(BaseModel):
    text: str = "default"


class StubOutput(BaseModel):
    result: str = ""


class StubAdapter(BaseAdapter):
    service_name = "test_svc"
    method_name = "test_method"
    input_schema = StubInput
    output_schema = StubOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        data = input_data if isinstance(input_data, StubInput) else StubInput.model_validate(input_data)
        return {"result": f"processed:{data.text}"}


class EmailStubAdapter(BaseAdapter):
    service_name = "email_connector"
    method_name = "fetch_emails"
    input_schema = StubInput
    output_schema = StubOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        return {"result": "emails_fetched"}


class ClassifyStubAdapter(BaseAdapter):
    service_name = "classifier"
    method_name = "classify"
    input_schema = StubInput
    output_schema = StubOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        data = input_data if isinstance(input_data, StubInput) else StubInput.model_validate(input_data)
        return {"result": f"classified:{data.text}"}


@pytest.fixture
def registry():
    reg = AdapterRegistry()
    reg.register(StubAdapter())
    reg.register(EmailStubAdapter())
    reg.register(ClassifyStubAdapter())
    return reg


@pytest.fixture
def compiler(registry):
    return PipelineCompiler(registry)


# --- Compilation tests ---


class TestCompileBasic:
    def test_single_step(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "simple",
            "steps": [
                {"name": "s1", "service": "test_svc", "method": "test_method"}
            ],
        })
        result = compiler.compile(pipeline)
        assert "s1" in result.step_funcs
        assert result.pipeline_def.name == "simple"

    def test_multi_step_with_deps(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "chain",
            "steps": [
                {
                    "name": "fetch",
                    "service": "email_connector",
                    "method": "fetch_emails",
                },
                {
                    "name": "classify",
                    "service": "classifier",
                    "method": "classify",
                    "depends_on": ["fetch"],
                },
            ],
        })
        result = compiler.compile(pipeline)
        assert len(result.step_funcs) == 2

        order = result.dag.topological_sort()
        assert order.index("fetch") < order.index("classify")

    def test_dag_nodes_have_metadata(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "meta",
            "steps": [
                {
                    "name": "s1",
                    "service": "test_svc",
                    "method": "test_method",
                    "for_each": "{{ input.items }}",
                    "condition": "output.x == 1",
                },
            ],
        })
        result = compiler.compile(pipeline)
        node = result.dag.get_node("s1")
        assert node.metadata["service"] == "test_svc"
        assert node.metadata["has_for_each"] is True
        assert node.metadata["has_condition"] is True


class TestCompileErrors:
    def test_missing_adapter(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "bad",
            "steps": [
                {"name": "s1", "service": "nonexistent", "method": "nope"}
            ],
        })
        with pytest.raises(PipelineCompileError, match="Missing adapters"):
            compiler.compile(pipeline)

    def test_cyclic_dependency(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "cycle",
            "steps": [
                {
                    "name": "a",
                    "service": "test_svc",
                    "method": "test_method",
                    "depends_on": ["b"],
                },
                {
                    "name": "b",
                    "service": "test_svc",
                    "method": "test_method",
                    "depends_on": ["a"],
                },
            ],
        })
        with pytest.raises(PipelineCompileError, match="DAG validation"):
            compiler.compile(pipeline)


class TestStepExecution:
    @pytest.mark.asyncio
    async def test_step_func_runs(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "exec",
            "steps": [
                {
                    "name": "s1",
                    "service": "test_svc",
                    "method": "test_method",
                    "config": {"text": "hello"},
                },
            ],
        })
        result = compiler.compile(pipeline)
        step_fn = result.step_funcs["s1"]
        ctx = ExecutionContext()
        output = await step_fn(ctx, {"input": {}})
        assert output["result"] == "processed:hello"

    @pytest.mark.asyncio
    async def test_step_func_with_jinja(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "jinja",
            "steps": [
                {
                    "name": "s1",
                    "service": "test_svc",
                    "method": "test_method",
                    "config": {"text": "{{ input.name }}"},
                },
            ],
        })
        result = compiler.compile(pipeline)
        step_fn = result.step_funcs["s1"]
        ctx = ExecutionContext()
        output = await step_fn(ctx, {"input": {"name": "world"}})
        assert output["result"] == "processed:world"

    @pytest.mark.asyncio
    async def test_step_func_chained_context(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "chain",
            "steps": [
                {
                    "name": "fetch",
                    "service": "email_connector",
                    "method": "fetch_emails",
                },
                {
                    "name": "classify",
                    "service": "classifier",
                    "method": "classify",
                    "depends_on": ["fetch"],
                    "config": {
                        "text": "{{ fetch.output.result }}",
                    },
                },
            ],
        })
        result = compiler.compile(pipeline)
        ctx = ExecutionContext()

        # Simulate pipeline execution: step 1 output → step 2 input
        out1 = await result.step_funcs["fetch"](ctx, {"input": {}})
        pipeline_ctx = {
            "input": {},
            "fetch": {"output": out1},
        }
        out2 = await result.step_funcs["classify"](ctx, pipeline_ctx)
        assert "classified:emails_fetched" == out2["result"]


class TestCompilationResultRepr:
    def test_repr(self, compiler):
        pipeline = PipelineDefinition.model_validate({
            "name": "test",
            "steps": [
                {"name": "s1", "service": "test_svc", "method": "test_method"},
            ],
        })
        result = compiler.compile(pipeline)
        r = repr(result)
        assert "test" in r
        assert "s1" in r
