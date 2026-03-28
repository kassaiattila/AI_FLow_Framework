"""
@test_registry:
    suite: core-unit
    component: core.context
    covers: [src/aiflow/core/context.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [context, execution, trace]
"""
from aiflow.core.context import ExecutionContext, TraceContext


class TestTraceContext:
    def test_default_trace_id_generated(self):
        tc = TraceContext()
        assert tc.trace_id is not None
        assert len(tc.trace_id) > 0

    def test_custom_trace_id(self):
        tc = TraceContext(trace_id="custom-123")
        assert tc.trace_id == "custom-123"


class TestExecutionContext:
    def test_default_run_id_generated(self):
        ctx = ExecutionContext()
        assert ctx.run_id is not None
        assert len(ctx.run_id) > 0

    def test_default_budget(self):
        ctx = ExecutionContext()
        assert ctx.budget_remaining_usd == 10.0

    def test_default_prompt_label(self):
        ctx = ExecutionContext()
        assert ctx.prompt_label == "prod"

    def test_custom_values(self):
        ctx = ExecutionContext(
            run_id="run-001",
            team_id="finance",
            user_id="user@example.com",
            prompt_label="dev",
            budget_remaining_usd=5.0,
        )
        assert ctx.run_id == "run-001"
        assert ctx.team_id == "finance"
        assert ctx.prompt_label == "dev"

    def test_with_budget_decrease(self):
        ctx = ExecutionContext(budget_remaining_usd=10.0)
        new_ctx = ctx.with_budget_decrease(3.5)
        assert new_ctx.budget_remaining_usd == 6.5
        assert ctx.budget_remaining_usd == 10.0  # original unchanged

    def test_with_checkpoint(self):
        ctx = ExecutionContext()
        assert ctx.checkpoint_version == 0
        new_ctx = ctx.with_checkpoint({"step": "extract", "data": {"key": "val"}})
        assert new_ctx.checkpoint_version == 1
        assert new_ctx.checkpoint_data == {"step": "extract", "data": {"key": "val"}}
        assert ctx.checkpoint_version == 0  # original unchanged

    def test_dry_run_flag(self):
        ctx = ExecutionContext(dry_run=True)
        assert ctx.dry_run is True

    def test_metadata(self):
        ctx = ExecutionContext(metadata={"source": "api"})
        assert ctx.metadata["source"] == "api"

    def test_trace_context_embedded(self):
        ctx = ExecutionContext()
        assert ctx.trace_context is not None
        assert ctx.trace_context.trace_id is not None
