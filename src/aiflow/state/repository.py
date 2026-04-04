"""Async repository for workflow and step run persistence.

All database operations go through this layer. Never use Session directly in business logic.
"""
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aiflow.state.models import StepRunModel, WorkflowRunModel

__all__ = ["StateRepository", "create_session_factory"]

logger = structlog.get_logger(__name__)


def create_session_factory(database_url: str, pool_size: int = 20, echo: bool = False) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory from a database URL."""
    engine = create_async_engine(database_url, pool_size=pool_size, echo=echo)
    return async_sessionmaker(engine, expire_on_commit=False)


class StateRepository:
    """Async repository for workflow_runs and step_runs tables."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # === Workflow Runs ===

    async def create_workflow_run(
        self,
        workflow_name: str,
        workflow_version: str,
        input_data: dict[str, Any],
        *,
        skill_name: str | None = None,
        team_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        priority: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunModel:
        """Create a new workflow run record."""
        run = WorkflowRunModel(
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            input_data=input_data,
            skill_name=skill_name,
            team_id=team_id,
            user_id=user_id,
            priority=priority,
            metadata_=metadata or {},
        )
        async with self._session_factory() as session:
            session.add(run)
            await session.commit()
            await session.refresh(run)
        logger.info("workflow_run_created", run_id=str(run.id), workflow=workflow_name)
        return run

    async def get_workflow_run(self, run_id: uuid.UUID) -> WorkflowRunModel | None:
        """Get a workflow run by ID."""
        async with self._session_factory() as session:
            return await session.get(WorkflowRunModel, run_id)

    async def update_workflow_run_status(
        self,
        run_id: uuid.UUID,
        status: str,
        *,
        output_data: dict[str, Any] | None = None,
        error: str | None = None,
        error_type: str | None = None,
        total_cost_usd: float | None = None,
        trace_id: str | None = None,
        trace_url: str | None = None,
    ) -> None:
        """Update workflow run status and optional fields."""
        values: dict[str, Any] = {"status": status}
        now = datetime.now(UTC)

        if status == "running":
            values["started_at"] = now
        elif status in ("completed", "failed", "cancelled"):
            values["completed_at"] = now

        if output_data is not None:
            values["output_data"] = output_data
        if error is not None:
            values["error"] = error
            values["error_type"] = error_type
        if total_cost_usd is not None:
            values["total_cost_usd"] = total_cost_usd
        if trace_id is not None:
            values["trace_id"] = trace_id
            values["trace_url"] = trace_url

        async with self._session_factory() as session:
            await session.execute(
                update(WorkflowRunModel).where(WorkflowRunModel.id == run_id).values(**values)
            )
            await session.commit()
        logger.info("workflow_run_updated", run_id=str(run_id), status=status)

    async def list_workflow_runs(
        self,
        *,
        status: str | None = None,
        workflow_name: str | None = None,
        skill_name: str | None = None,
        team_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowRunModel]:
        """List workflow runs with optional filters."""
        stmt = select(WorkflowRunModel).order_by(WorkflowRunModel.created_at.desc())
        if status:
            stmt = stmt.where(WorkflowRunModel.status == status)
        if workflow_name:
            stmt = stmt.where(WorkflowRunModel.workflow_name == workflow_name)
        if skill_name:
            stmt = stmt.where(WorkflowRunModel.skill_name == skill_name)
        if team_id:
            stmt = stmt.where(WorkflowRunModel.team_id == team_id)
        stmt = stmt.limit(limit).offset(offset)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # === Step Runs ===

    async def create_step_run(
        self,
        workflow_run_id: uuid.UUID,
        step_name: str,
        step_index: int,
        *,
        input_data: dict[str, Any] | None = None,
    ) -> StepRunModel:
        """Create a new step run record."""
        step = StepRunModel(
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            step_index=step_index,
            input_data=input_data,
        )
        async with self._session_factory() as session:
            session.add(step)
            await session.commit()
            await session.refresh(step)
        return step

    async def update_step_run(
        self,
        step_id: uuid.UUID,
        *,
        status: str | None = None,
        output_data: dict[str, Any] | None = None,
        error: str | None = None,
        error_type: str | None = None,
        duration_ms: float | None = None,
        cost_usd: float | None = None,
        model_used: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        scores: dict[str, float] | None = None,
        quality_gate_passed: bool | None = None,
        checkpoint_data: dict[str, Any] | None = None,
        retry_count: int | None = None,
    ) -> None:
        """Update step run with execution results."""
        values: dict[str, Any] = {}
        now = datetime.now(UTC)

        if status is not None:
            values["status"] = status
            if status == "running":
                values["started_at"] = now
            elif status in ("completed", "failed", "skipped"):
                values["completed_at"] = now

        for key, val in [
            ("output_data", output_data), ("error", error), ("error_type", error_type),
            ("duration_ms", duration_ms), ("cost_usd", cost_usd), ("model_used", model_used),
            ("input_tokens", input_tokens), ("output_tokens", output_tokens),
            ("scores", scores), ("quality_gate_passed", quality_gate_passed),
            ("checkpoint_data", checkpoint_data), ("retry_count", retry_count),
        ]:
            if val is not None:
                values[key] = val

        if checkpoint_data is not None:
            values["checkpoint_version"] = StepRunModel.checkpoint_version + 1

        if values:
            async with self._session_factory() as session:
                await session.execute(
                    update(StepRunModel).where(StepRunModel.id == step_id).values(**values)
                )
                await session.commit()

    async def get_step_runs(self, workflow_run_id: uuid.UUID) -> list[StepRunModel]:
        """Get all step runs for a workflow run, ordered by step_index."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(StepRunModel)
                .where(StepRunModel.workflow_run_id == workflow_run_id)
                .order_by(StepRunModel.step_index)
            )
            return list(result.scalars().all())

    async def get_latest_checkpoint(self, workflow_run_id: uuid.UUID) -> dict[str, Any] | None:
        """Get the checkpoint data from the last completed step."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(StepRunModel)
                .where(
                    StepRunModel.workflow_run_id == workflow_run_id,
                    StepRunModel.checkpoint_data.isnot(None),
                )
                .order_by(StepRunModel.step_index.desc())
                .limit(1)
            )
            step = result.scalar_one_or_none()
            return step.checkpoint_data if step else None
