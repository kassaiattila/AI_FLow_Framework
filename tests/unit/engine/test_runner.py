"""
@test_registry:
    suite: engine-unit
    component: engine.runner
    covers: [src/aiflow/engine/runner.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 800
    requires_services: []
    tags: [engine, runner, execution, workflow, async]
"""
import pytest
from aiflow.core.context import ExecutionContext
from aiflow.core.types import Status
from aiflow.core.errors import BudgetExceededError
from aiflow.engine.step import step
from aiflow.engine.dag import DAG
from aiflow.engine.runner import WorkflowRunner
from aiflow.engine.checkpoint import CheckpointManager


# Test steps
@step(name="upper")
async def upper_step(data):
    text = data if isinstance(data, str) else data.get("text", data.get("result", ""))
    return {"result": text.upper()}

@step(name="add_prefix")
async def prefix_step(data):
    text = data.get("result", "") if isinstance(data, dict) else str(data)
    return {"result": f"PREFIX_{text}"}

@step(name="failing")
async def failing_step(data):
    raise ValueError("intentional failure")

@step(name="costly")
async def costly_step(data):
    return {"result": "expensive", "cost": 5.0}


def _build_linear_dag():
    """Build: upper -> add_prefix"""
    dag = DAG()
    dag.add_node("upper", step_func=upper_step)
    dag.add_node("add_prefix", step_func=prefix_step)
    dag.add_edge("upper", "add_prefix")
    return dag, {"upper": upper_step, "add_prefix": prefix_step}


class TestWorkflowRunner:
    @pytest.fixture
    def runner(self):
        return WorkflowRunner()

    async def test_linear_workflow(self, runner):
        dag, funcs = _build_linear_dag()
        result = await runner.run("test-wf", dag, funcs, {"text": "hello"})
        assert result.status == Status.COMPLETED
        assert result.steps_completed == 2
        assert result.output_data["result"] == "PREFIX_HELLO"

    async def test_single_step_workflow(self, runner):
        dag = DAG()
        dag.add_node("upper", step_func=upper_step)
        result = await runner.run("single", dag, {"upper": upper_step}, {"text": "test"})
        assert result.status == Status.COMPLETED
        assert result.output_data["result"] == "TEST"

    async def test_workflow_failure(self, runner):
        dag = DAG()
        dag.add_node("failing", step_func=failing_step)
        result = await runner.run("fail-wf", dag, {"failing": failing_step}, {})
        assert result.status == Status.FAILED
        assert "intentional failure" in result.error

    async def test_budget_exceeded(self, runner):
        dag = DAG()
        dag.add_node("upper", step_func=upper_step)
        ctx = ExecutionContext(budget_remaining_usd=0.0)
        result = await runner.run("budget-wf", dag, {"upper": upper_step}, {"text": "x"}, ctx=ctx)
        assert result.status == Status.FAILED
        assert "Budget" in result.error or "budget" in result.error.lower()

    async def test_records_duration(self, runner):
        dag, funcs = _build_linear_dag()
        result = await runner.run("timed", dag, funcs, {"text": "hello"})
        assert result.total_duration_ms >= 0
        assert result.total_duration_ms is not None

    async def test_checkpoint_saved(self):
        mgr = CheckpointManager()
        runner = WorkflowRunner(checkpoint_manager=mgr)
        dag, funcs = _build_linear_dag()
        ctx = ExecutionContext(run_id="ckpt-test")
        await runner.run("ckpt-wf", dag, funcs, {"text": "hello"}, ctx=ctx)
        latest = mgr.get_latest("ckpt-test")
        assert latest is not None
        assert "upper" in latest.completed_steps
        assert "add_prefix" in latest.completed_steps

    async def test_steps_total_reported(self, runner):
        dag, funcs = _build_linear_dag()
        result = await runner.run("total", dag, funcs, {"text": "x"})
        assert result.steps_total == 2
        assert result.steps_completed == 2
