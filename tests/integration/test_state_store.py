"""
@test_registry:
    suite: integration-state
    component: state.*
    covers: [src/aiflow/state/models.py, src/aiflow/state/repository.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, state, postgres, async]
"""

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aiflow.state.repository import StateRepository

# Use Docker Compose DB (port 5433) or override via env
DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def repo():
    """Create repository instance with fresh engine per test."""
    try:
        eng = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
        # Verify connection
        async with eng.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    factory = async_sessionmaker(eng, expire_on_commit=False)
    repository = StateRepository(factory)
    yield repository

    # Clean up test data
    async with eng.begin() as conn:
        await conn.execute(sa_text("DELETE FROM step_runs"))
        await conn.execute(sa_text("DELETE FROM workflow_runs"))
    await eng.dispose()


class TestWorkflowRunCRUD:
    @pytest.mark.asyncio
    async def test_create_workflow_run(self, repo):
        run = await repo.create_workflow_run(
            workflow_name="test-workflow",
            workflow_version="1.0.0",
            input_data={"message": "hello"},
            skill_name="test_skill",
        )
        assert run.id is not None
        assert run.workflow_name == "test-workflow"
        assert run.status == "pending"

    @pytest.mark.asyncio
    async def test_get_workflow_run(self, repo):
        run = await repo.create_workflow_run(
            workflow_name="get-test",
            workflow_version="1.0.0",
            input_data={"key": "value"},
        )
        fetched = await repo.get_workflow_run(run.id)
        assert fetched is not None
        assert fetched.workflow_name == "get-test"
        assert fetched.input_data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get_workflow_run(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_to_running(self, repo):
        run = await repo.create_workflow_run(
            workflow_name="status-test",
            workflow_version="1.0.0",
            input_data={},
        )
        await repo.update_workflow_run_status(run.id, "running", trace_id="trace-123")
        updated = await repo.get_workflow_run(run.id)
        assert updated.status == "running"
        assert updated.started_at is not None
        assert updated.trace_id == "trace-123"

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self, repo):
        run = await repo.create_workflow_run(
            workflow_name="complete-test",
            workflow_version="1.0.0",
            input_data={},
        )
        await repo.update_workflow_run_status(run.id, "running")
        await repo.update_workflow_run_status(
            run.id,
            "completed",
            output_data={"result": "ok"},
            total_cost_usd=0.05,
        )
        updated = await repo.get_workflow_run(run.id)
        assert updated.status == "completed"
        assert updated.completed_at is not None
        assert updated.output_data == {"result": "ok"}
        assert updated.total_cost_usd == 0.05

    @pytest.mark.asyncio
    async def test_update_status_to_failed(self, repo):
        run = await repo.create_workflow_run(
            workflow_name="fail-test",
            workflow_version="1.0.0",
            input_data={},
        )
        await repo.update_workflow_run_status(
            run.id,
            "failed",
            error="timeout occurred",
            error_type="LLMTimeoutError",
        )
        updated = await repo.get_workflow_run(run.id)
        assert updated.status == "failed"
        assert updated.error == "timeout occurred"
        assert updated.error_type == "LLMTimeoutError"

    @pytest.mark.asyncio
    async def test_list_workflow_runs(self, repo):
        for i in range(3):
            await repo.create_workflow_run(
                workflow_name=f"list-test-{i}",
                workflow_version="1.0.0",
                input_data={},
            )
        runs = await repo.list_workflow_runs(limit=10)
        assert len(runs) >= 3

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, repo):
        run = await repo.create_workflow_run(
            workflow_name="filter-test",
            workflow_version="1.0.0",
            input_data={},
        )
        await repo.update_workflow_run_status(run.id, "completed")
        completed = await repo.list_workflow_runs(status="completed")
        assert all(r.status == "completed" for r in completed)


class TestStepRunCRUD:
    @pytest.mark.asyncio
    async def test_create_step_run(self, repo):
        wf = await repo.create_workflow_run(
            workflow_name="step-parent",
            workflow_version="1.0.0",
            input_data={},
        )
        step = await repo.create_step_run(
            workflow_run_id=wf.id,
            step_name="classify",
            step_index=0,
            input_data={"text": "hello"},
        )
        assert step.id is not None
        assert step.step_name == "classify"
        assert step.step_index == 0

    @pytest.mark.asyncio
    async def test_update_step_run(self, repo):
        wf = await repo.create_workflow_run(
            workflow_name="step-update",
            workflow_version="1.0.0",
            input_data={},
        )
        step = await repo.create_step_run(wf.id, "extract", 1)
        await repo.update_step_run(
            step.id,
            status="completed",
            output_data={"entities": ["A", "B"]},
            duration_ms=1234.5,
            cost_usd=0.02,
            model_used="openai/gpt-4o",
            input_tokens=500,
            output_tokens=200,
            scores={"completeness": 0.92},
        )
        steps = await repo.get_step_runs(wf.id)
        updated = steps[0]
        assert updated.status == "completed"
        assert updated.duration_ms == 1234.5
        assert updated.scores == {"completeness": 0.92}

    @pytest.mark.asyncio
    async def test_get_step_runs_ordered(self, repo):
        wf = await repo.create_workflow_run(
            workflow_name="step-order",
            workflow_version="1.0.0",
            input_data={},
        )
        await repo.create_step_run(wf.id, "step_c", 2)
        await repo.create_step_run(wf.id, "step_a", 0)
        await repo.create_step_run(wf.id, "step_b", 1)
        steps = await repo.get_step_runs(wf.id)
        assert [s.step_name for s in steps] == ["step_a", "step_b", "step_c"]

    @pytest.mark.asyncio
    async def test_checkpoint_save_and_retrieve(self, repo):
        wf = await repo.create_workflow_run(
            workflow_name="checkpoint-test",
            workflow_version="1.0.0",
            input_data={},
        )
        step = await repo.create_step_run(wf.id, "extract", 0)
        await repo.update_step_run(
            step.id,
            status="completed",
            checkpoint_data={"key": "value", "step": "extract"},
        )
        checkpoint = await repo.get_latest_checkpoint(wf.id)
        assert checkpoint is not None
        assert checkpoint["key"] == "value"

    @pytest.mark.asyncio
    async def test_no_checkpoint_returns_none(self, repo):
        wf = await repo.create_workflow_run(
            workflow_name="no-checkpoint",
            workflow_version="1.0.0",
            input_data={},
        )
        checkpoint = await repo.get_latest_checkpoint(wf.id)
        assert checkpoint is None
