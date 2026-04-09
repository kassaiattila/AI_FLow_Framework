"""
@test_registry:
    suite: core-unit
    component: state.models
    covers: [src/aiflow/state/models.py]
    phase: 1
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [state, orm, models]
"""

import uuid

from aiflow.state.models import Base, StepRunModel, WorkflowRunModel


class TestWorkflowRunModel:
    def test_create_instance(self):
        run = WorkflowRunModel(
            workflow_name="test-workflow",
            workflow_version="1.0.0",
            input_data={"message": "hello"},
        )
        assert run.workflow_name == "test-workflow"
        # SQLAlchemy server/column defaults are applied at flush, not construction
        # So we test that explicit values work correctly
        assert run.workflow_version == "1.0.0"
        assert run.input_data == {"message": "hello"}

    def test_create_instance_with_explicit_defaults(self):
        run = WorkflowRunModel(
            workflow_name="test-workflow",
            workflow_version="1.0.0",
            input_data={"message": "hello"},
            status="pending",
            priority=3,
            total_cost_usd=0.0,
        )
        assert run.status == "pending"
        assert run.priority == 3
        assert run.total_cost_usd == 0.0

    def test_repr(self):
        run = WorkflowRunModel(
            id=uuid.uuid4(),
            workflow_name="test",
            workflow_version="1.0",
            input_data={},
            status="running",
        )
        assert "test" in repr(run)
        assert "running" in repr(run)

    def test_table_name(self):
        assert WorkflowRunModel.__tablename__ == "workflow_runs"

    def test_base_metadata_has_tables(self):
        assert "workflow_runs" in Base.metadata.tables
        assert "step_runs" in Base.metadata.tables


class TestStepRunModel:
    def test_create_instance(self):
        step = StepRunModel(
            workflow_run_id=uuid.uuid4(),
            step_name="classify",
            step_index=0,
        )
        assert step.step_name == "classify"
        assert step.step_index == 0

    def test_create_instance_with_explicit_defaults(self):
        step = StepRunModel(
            workflow_run_id=uuid.uuid4(),
            step_name="classify",
            step_index=0,
            status="pending",
            retry_count=0,
            cost_usd=0.0,
        )
        assert step.status == "pending"
        assert step.retry_count == 0
        assert step.cost_usd == 0.0

    def test_repr(self):
        step = StepRunModel(
            id=uuid.uuid4(),
            workflow_run_id=uuid.uuid4(),
            step_name="extract",
            step_index=1,
            status="completed",
        )
        assert "extract" in repr(step)

    def test_checkpoint_defaults(self):
        step = StepRunModel(
            workflow_run_id=uuid.uuid4(),
            step_name="test",
            step_index=0,
        )
        assert step.checkpoint_data is None
        # checkpoint_version default is applied at DB flush; verify None pre-flush
        assert step.checkpoint_version is None

    def test_checkpoint_explicit(self):
        step = StepRunModel(
            workflow_run_id=uuid.uuid4(),
            step_name="test",
            step_index=0,
            checkpoint_version=0,
        )
        assert step.checkpoint_version == 0
