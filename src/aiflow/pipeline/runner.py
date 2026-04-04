"""PipelineRunner — end-to-end pipeline execution with DB persistence.

Orchestrates: parse → compile → create workflow_run → execute steps → update run.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.core.context import ExecutionContext
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
    ) -> None:
        self._compiler = PipelineCompiler(registry)
        self._parser = PipelineParser()
        self._repo = PipelineRepository(session_factory)
        self._sf = session_factory

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
        """Core execution: compile → create run → execute steps → update run."""
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

        logger.info(
            "pipeline_run_started",
            run_id=str(run_id),
            pipeline=pipeline_def.name,
            steps=len(pipeline_def.steps),
        )

        # Execute steps in topological order
        pipeline_context: dict[str, Any] = {"input": input_data}
        step_outputs: dict[str, Any] = {}
        error: str | None = None
        status = "completed"

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

            try:
                output = await step_func(ctx, pipeline_context)
                step_duration = (time.monotonic() - step_start) * 1000

                step_outputs[step_name] = output
                pipeline_context[step_name] = {"output": output}

                async with self._sf() as session:
                    step_run = await session.get(StepRunModel, step_run_id)
                    if step_run:
                        step_run.status = "completed"
                        step_run.output_data = output
                        step_run.duration_ms = step_duration
                        step_run.completed_at = datetime.now(UTC)
                        await session.commit()

                logger.info(
                    "pipeline_step_completed",
                    run_id=str(run_id),
                    step=step_name,
                    duration_ms=round(step_duration, 1),
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
                wf_run.completed_at = datetime.now(UTC)
                await session.commit()

        logger.info(
            "pipeline_run_finished",
            run_id=str(run_id),
            pipeline=pipeline_def.name,
            status=status,
            duration_ms=round(total_duration, 1),
        )

        return PipelineRunResult(
            run_id=run_id,
            pipeline_name=pipeline_def.name,
            status=status,
            step_outputs=step_outputs,
            total_duration_ms=total_duration,
            error=error,
        )
