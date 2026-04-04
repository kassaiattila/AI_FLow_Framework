"""Pipeline compiler — transform PipelineDefinition into executable DAG.

Bridges the gap between YAML pipeline definitions and the existing
WorkflowRunner DAG engine.
"""

from __future__ import annotations

from typing import Any

import structlog

from aiflow.core.context import ExecutionContext
from aiflow.engine.conditions import Condition
from aiflow.engine.dag import DAG
from aiflow.pipeline.adapter_base import AdapterRegistry, BaseAdapter
from aiflow.pipeline.schema import PipelineDefinition, PipelineStepDef
from aiflow.pipeline.template import TemplateResolver

__all__ = ["CompilationResult", "PipelineCompiler", "PipelineCompileError"]

logger = structlog.get_logger(__name__)


class PipelineCompileError(Exception):
    """Raised when pipeline compilation fails."""


class CompilationResult:
    """Result of pipeline compilation: DAG + step functions."""

    def __init__(
        self,
        dag: DAG,
        step_funcs: dict[str, Any],
        pipeline_def: PipelineDefinition,
    ) -> None:
        self.dag = dag
        self.step_funcs = step_funcs
        self.pipeline_def = pipeline_def

    def __repr__(self) -> str:
        return (
            f"CompilationResult(pipeline={self.pipeline_def.name!r}, "
            f"steps={list(self.step_funcs.keys())})"
        )


class PipelineCompiler:
    """Compile a PipelineDefinition into a DAG with executable step functions.

    1. Validate all steps reference registered adapters
    2. Create DAGNode per step with wrapped adapter.execute()
    3. Create DAGEdge per depends_on with optional conditions
    4. Validate the resulting DAG (no cycles, all refs exist)
    """

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry
        self._resolver = TemplateResolver()

    def compile(
        self,
        pipeline_def: PipelineDefinition,
    ) -> CompilationResult:
        """Compile pipeline definition into executable DAG + step functions.

        Returns CompilationResult with dag, step_funcs, and pipeline_def.
        Raises PipelineCompileError if adapters missing or DAG invalid.
        """
        self._validate_adapters(pipeline_def)

        dag = DAG()
        step_funcs: dict[str, Any] = {}

        for step_def in pipeline_def.steps:
            step_func = self._build_step_func(step_def)
            step_funcs[step_def.name] = step_func

            dag.add_node(
                name=step_def.name,
                step_func=step_func,
                metadata={
                    "service": step_def.service,
                    "method": step_def.method,
                    "has_for_each": step_def.for_each is not None,
                    "has_condition": step_def.condition is not None,
                },
            )

        for step_def in pipeline_def.steps:
            for dep_name in step_def.depends_on:
                condition = None
                if step_def.condition:
                    condition = Condition(
                        expression=step_def.condition,
                        target_steps=[step_def.name],
                    )
                dag.add_edge(
                    from_node=dep_name,
                    to_node=step_def.name,
                    condition=condition,
                )

        dag_errors = dag.validate()
        if dag_errors:
            raise PipelineCompileError(
                f"DAG validation failed: {'; '.join(dag_errors)}"
            )

        logger.info(
            "pipeline_compiled",
            pipeline=pipeline_def.name,
            steps=len(step_funcs),
            edges=dag.edge_count,
        )

        return CompilationResult(
            dag=dag, step_funcs=step_funcs, pipeline_def=pipeline_def
        )

    def _validate_adapters(self, pipeline_def: PipelineDefinition) -> None:
        """Ensure all steps reference registered adapters."""
        missing: list[str] = []
        for step in pipeline_def.steps:
            if not self._registry.has(step.service, step.method):
                missing.append(f"{step.name} → ({step.service}, {step.method})")

        if missing:
            raise PipelineCompileError(
                f"Missing adapters: {'; '.join(missing)}. "
                f"Available: {self._registry.list_adapters()}"
            )

    def _build_step_func(self, step_def: PipelineStepDef) -> Any:
        """Build an async callable that wraps adapter.execute with template resolution."""
        adapter = self._registry.get(step_def.service, step_def.method)
        resolver = self._resolver

        async def step_func(
            ctx: ExecutionContext,
            pipeline_context: dict[str, Any],
        ) -> dict[str, Any]:
            """Execute one pipeline step with Jinja2 config resolution."""
            if step_def.for_each and isinstance(adapter, BaseAdapter):
                items_expr = step_def.for_each
                items = resolver.resolve_expression(
                    items_expr, pipeline_context
                )
                if not isinstance(items, list):
                    items = [items]

                if not items:
                    return {"results": [], "count": 0}

                results = await adapter.execute_for_each(
                    items=[
                        resolver.resolve_config(
                            step_def.config,
                            {**pipeline_context, "item": item},
                        )
                        for item in items
                    ],
                    config={},
                    ctx=ctx,
                    concurrency=step_def.concurrency,
                )
                return {"results": results, "count": len(results)}

            resolved_config = resolver.resolve_config(
                step_def.config, pipeline_context
            )
            return await adapter.execute(resolved_config, {}, ctx)

        step_func.__name__ = f"step_{step_def.name}"
        step_func.__qualname__ = f"PipelineCompiler.step_{step_def.name}"
        return step_func
