"""PipelineRunner — end-to-end pipeline execution with DB persistence.

Orchestrates: parse → compile → create workflow_run → execute steps → update run.
Integrates with Langfuse tracing and cost_records persistence.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.core.context import ExecutionContext
from aiflow.observability.tracing import TraceManager
from aiflow.pipeline.adapter_base import AdapterRegistry
from aiflow.pipeline.compiler import PipelineCompiler
from aiflow.pipeline.parser import PipelineParser
from aiflow.pipeline.repository import PipelineRepository
from aiflow.pipeline.schema import PipelineDefinition
from aiflow.state.models import StepRunModel, WorkflowRunModel

__all__ = ["PipelineRunner", "PipelineRunResult"]

logger = structlog.get_logger(__name__)


class PipelineRunResult:
    """Result of a pipeline execution."""

    def __init__(
        self,
        *,
        run_id: uuid.UUID,
        pipeline_name: str,
        status: str,
        step_outputs: dict[str, Any],
        total_duration_ms: float,
        error: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.pipeline_name = pipeline_name
        self.status = status
        self.step_outputs = step_outputs
        self.total_duration_ms = total_duration_ms
        self.error = error

    @property
    def success(self) -> bool:
        return self.status == "completed"

    def __repr__(self) -> str:
        return (
            f"PipelineRunResult(run_id={self.run_id!s}, "
            f"pipeline={self.pipeline_name!r}, status={self.status!r})"
        )


class PipelineRunner:
    """Execute YAML pipelines with DB persistence.

    Usage:
        runner = PipelineRunner(registry, session_factory)
        result = await runner.run(pipeline_id, {"connector_id": "cfg-1"})
        result = await runner.run_from_yaml(yaml_str, {"connector_id": "cfg-1"})
    """

    def __init__(
        self,
        registry: AdapterRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        trace_manager: TraceManager | None = None,
    ) -> None:
        self._compiler = PipelineCompiler(registry)
        self._parser = PipelineParser()
        self._repo = PipelineRepository(session_factory)
        self._sf = session_factory
        self._trace_manager = trace_manager

    async def run(
        self,
        pipeline_id: uuid.UUID,
        input_data: dict[str, Any],
        ctx: ExecutionContext | None = None,
    ) -> PipelineRunResult:
        """Load pipeline from DB → compile → execute → persist results."""
        model = await self._repo.get_by_id(pipeline_id)
        if model is None:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        pipeline_def = PipelineDefinition.model_validate(model.definition)
        return await self._execute(
            pipeline_def=pipeline_def,
            input_data=input_data,
            ctx=ctx or ExecutionContext(),
            pipeline_id=pipeline_id,
        )

    async def run_from_yaml(
        self,
        yaml_str: str,
        input_data: dict[str, Any],
        ctx: ExecutionContext | None = None,
    ) -> PipelineRunResult:
        """Parse YAML on-the-fly, execute, persist results (ad-hoc run)."""
        pipeline_def = self._parser.parse_yaml(yaml_str)
        return await self._execute(
            pipeline_def=pipeline_def,
            input_data=input_data,
            ctx=ctx or ExecutionContext(),
            pipeline_id=None,
        )

    async def _execute(
        self,
        *,
        pipeline_def: PipelineDefinition,
        input_data: dict[str, Any],
        ctx: ExecutionContext,
        pipeline_id: uuid.UUID | None,
    ) -> PipelineRunResult:
        """Core execution: compile → create run → execute steps → update run.

        Integrates Langfuse tracing (trace per run, span per step) and
        persists step costs to cost_records table.
        """
        start = time.monotonic()
        compilation = self._compiler.compile(pipeline_def)

        # Create workflow run
        run_id = uuid.uuid4()
        async with self._sf() as session:
            wf_run = WorkflowRunModel(
                id=run_id,
                workflow_name=pipeline_def.name,
                workflow_version=pipeline_def.version,
                input_data=input_data,
                status="running",
                started_at=datetime.now(UTC),
                pipeline_id=pipeline_id,
                team_id=ctx.team_id,
                user_id=ctx.user_id,
            )
            session.add(wf_run)
            await session.commit()

        # Start Langfuse trace for the pipeline run
        trace_id: str | None = None
        if self._trace_manager:
            try:
                trace_id = await self._trace_manager.start_trace(
                    name=f"pipeline:{pipeline_def.name}",
                    metadata={
                        "run_id": str(run_id),
                        "pipeline_version": pipeline_def.version,
                        "steps": len(pipeline_def.steps),
                        "team_id": ctx.team_id,
                    },
                )
            except Exception as exc:
                logger.debug("langfuse_trace_start_failed", error=str(exc))

        logger.info(
            "pipeline_run_started",
            run_id=str(run_id),
            pipeline=pipeline_def.name,
            steps=len(pipeline_def.steps),
            trace_id=trace_id,
        )

        # Execute steps in topological order
        pipeline_context: dict[str, Any] = {"input": input_data}
        step_outputs: dict[str, Any] = {}
        error: str | None = None
        status = "completed"
        total_cost_usd: float = 0.0

        execution_order = compilation.dag.topological_sort()

        for step_idx, step_name in enumerate(execution_order):
            step_start = time.monotonic()
            step_func = compilation.step_funcs[step_name]

            step_run_id = uuid.uuid4()
            async with self._sf() as session:
                step_run = StepRunModel(
                    id=step_run_id,
                    workflow_run_id=run_id,
                    step_name=step_name,
                    step_index=step_idx,
                    status="running",
                    input_data=pipeline_context,
                    started_at=datetime.now(UTC),
                )
                session.add(step_run)
                await session.commit()

            # Start Langfuse span for this step
            span_id: str | None = None
            if self._trace_manager and trace_id:
                try:
                    span_id = await self._trace_manager.start_span(
                        trace_id=trace_id,
                        name=step_name,
                        metadata={"step_index": step_idx},
                    )
                except Exception:
                    pass

            try:
                output = await step_func(ctx, pipeline_context)
                step_duration = (time.monotonic() - step_start) * 1000

                step_outputs[step_name] = output
                pipeline_context[step_name] = {"output": output}

                # Extract cost info from step output if available
                step_cost = _extract_step_cost(output)
                total_cost_usd += step_cost

                # Persist cost to cost_records (best-effort)
                if step_cost > 0:
                    await _record_pipeline_cost(
                        run_id=run_id,
                        step_name=step_name,
                        output=output,
                        cost_usd=step_cost,
                        team_id=ctx.team_id,
                    )

                async with self._sf() as session:
                    step_run = await session.get(StepRunModel, step_run_id)
                    if step_run:
                        step_run.status = "completed"
                        step_run.output_data = output
                        step_run.duration_ms = step_duration
                        step_run.completed_at = datetime.now(UTC)
                        await session.commit()

                # End Langfuse span
                if self._trace_manager and trace_id and span_id:
                    try:
                        await self._trace_manager.end_span(
                            trace_id=trace_id,
                            span_id=span_id,
                            metadata={
                                "duration_ms": round(step_duration, 1),
                                "status": "completed",
                                "cost_usd": step_cost,
                            },
                        )
                    except Exception:
                        pass

                logger.info(
                    "pipeline_step_completed",
                    run_id=str(run_id),
                    step=step_name,
                    duration_ms=round(step_duration, 1),
                    cost_usd=round(step_cost, 6),
                )

            except Exception as exc:
                step_duration = (time.monotonic() - step_start) * 1000
                error = f"Step '{step_name}' failed: {exc}"
                status = "failed"

                async with self._sf() as session:
                    step_run = await session.get(StepRunModel, step_run_id)
                    if step_run:
                        step_run.status = "failed"
                        step_run.error = str(exc)
                        step_run.error_type = type(exc).__name__
                        step_run.duration_ms = step_duration
                        step_run.completed_at = datetime.now(UTC)
                        await session.commit()

                # End Langfuse span with error
                if self._trace_manager and trace_id and span_id:
                    try:
                        await self._trace_manager.end_span(
                            trace_id=trace_id,
                            span_id=span_id,
                            metadata={
                                "duration_ms": round(step_duration, 1),
                                "status": "failed",
                                "error": str(exc),
                            },
                        )
                    except Exception:
                        pass

                logger.error(
                    "pipeline_step_failed",
                    run_id=str(run_id),
                    step=step_name,
                    error=str(exc),
                )
                break

        # Finalize workflow run
        total_duration = (time.monotonic() - start) * 1000
        async with self._sf() as session:
            wf_run = await session.get(WorkflowRunModel, run_id)
            if wf_run:
                wf_run.status = status
                wf_run.output_data = step_outputs
                wf_run.error = error
                wf_run.total_duration_ms = total_duration
                wf_run.total_cost_usd = total_cost_usd
                wf_run.completed_at = datetime.now(UTC)
                await session.commit()

        # End Langfuse trace
        if self._trace_manager and trace_id:
            try:
                await self._trace_manager.end_trace(
                    trace_id=trace_id,
                    metadata={
                        "status": status,
                        "total_duration_ms": round(total_duration, 1),
                        "total_cost_usd": round(total_cost_usd, 6),
                        "steps_executed": len(step_outputs),
                    },
                )
            except Exception:
                pass

        logger.info(
            "pipeline_run_finished",
            run_id=str(run_id),
            pipeline=pipeline_def.name,
            status=status,
            duration_ms=round(total_duration, 1),
            total_cost_usd=round(total_cost_usd, 6),
            trace_id=trace_id,
        )

        return PipelineRunResult(
            run_id=run_id,
            pipeline_name=pipeline_def.name,
            status=status,
            step_outputs=step_outputs,
            total_duration_ms=total_duration,
            error=error,
        )


def _extract_step_cost(output: Any) -> float:
    """Extract cost_usd from step output dict (best-effort)."""
    if isinstance(output, dict):
        cost = output.get("cost_usd") or output.get("cost") or 0.0
        try:
            return float(cost)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


async def _record_pipeline_cost(
    *,
    run_id: uuid.UUID,
    step_name: str,
    output: Any,
    cost_usd: float,
    team_id: str | None,
) -> None:
    """Persist pipeline step cost to cost_records table (best-effort)."""
    try:
        from aiflow.api.cost_recorder import record_cost
        model = "unknown"
        input_tokens = 0
        output_tokens = 0
        if isinstance(output, dict):
            model = output.get("model", "unknown")
            input_tokens = int(output.get("input_tokens", 0))
            output_tokens = int(output.get("output_tokens", 0))
        await record_cost(
            workflow_run_id=run_id,
            step_name=step_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            team_id=str(team_id) if team_id else None,
        )
    except Exception as exc:
        logger.debug("pipeline_cost_record_failed", error=str(exc), step=step_name)
