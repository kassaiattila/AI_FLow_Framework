"""
@test_registry:
    suite: core-unit
    component: core.types
    covers: [src/aiflow/core/types.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [types, enums, models]
"""
import pytest
from aiflow.core.types import Status, StepStatus, Priority, SkillType, StepResult, WorkflowResult


class TestStatusEnum:
    def test_status_values(self):
        assert Status.PENDING == "pending"
        assert Status.RUNNING == "running"
        assert Status.COMPLETED == "completed"
        assert Status.FAILED == "failed"
        assert Status.PAUSED == "paused"
        assert Status.CANCELLED == "cancelled"

    def test_status_is_str(self):
        assert isinstance(Status.PENDING, str)

    def test_status_from_string(self):
        assert Status("completed") == Status.COMPLETED

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            Status("invalid")


class TestStepStatus:
    def test_step_status_includes_retrying(self):
        assert StepStatus.RETRYING == "retrying"

    def test_step_status_includes_skipped(self):
        assert StepStatus.SKIPPED == "skipped"


class TestPriority:
    def test_priority_values(self):
        assert Priority.CRITICAL == "critical"
        assert Priority.BACKGROUND == "background"


class TestSkillType:
    def test_skill_types(self):
        assert SkillType.AI == "ai"
        assert SkillType.RPA == "rpa"
        assert SkillType.HYBRID == "hybrid"


class TestStepResult:
    def test_default_values(self):
        result = StepResult(status=StepStatus.COMPLETED)
        assert result.cost_usd == 0.0
        assert result.scores == {}
        assert result.output_data is None

    def test_with_all_fields(self):
        result = StepResult(
            status=StepStatus.COMPLETED,
            output_data={"key": "value"},
            duration_ms=123.4,
            cost_usd=0.05,
            scores={"accuracy": 0.95},
        )
        assert result.output_data == {"key": "value"}
        assert result.scores["accuracy"] == 0.95

    def test_failed_result_with_error(self):
        result = StepResult(
            status=StepStatus.FAILED,
            error="Something went wrong",
            error_type="LLMTimeoutError",
        )
        assert result.error is not None
        assert result.error_type == "LLMTimeoutError"


class TestWorkflowResult:
    def test_default_values(self):
        result = WorkflowResult(status=Status.PENDING)
        assert result.total_cost_usd == 0.0
        assert result.steps_completed == 0

    def test_completed_workflow(self):
        result = WorkflowResult(
            status=Status.COMPLETED,
            output_data={"diagram": "mermaid code"},
            total_duration_ms=12000,
            total_cost_usd=0.058,
            steps_completed=5,
            steps_total=5,
        )
        assert result.steps_completed == result.steps_total
