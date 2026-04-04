"""
@test_registry:
    suite: core-unit
    component: observability.cost_tracker
    covers: [src/aiflow/observability/cost_tracker.py]
    phase: 6
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [observability, cost, budget, tracking]
"""
import pytest

from aiflow.observability.cost_tracker import (
    BudgetAlert,
    BudgetStatus,
    CostRecord,
    CostTracker,
)


class TestCostRecord:
    """Verify CostRecord data model."""

    def test_create_cost_record(self):
        record = CostRecord(
            workflow_run_id="run-001",
            step_name="summarize",
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.005,
            team_id="team-alpha",
        )
        assert record.model == "gpt-4o"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.cost_usd == 0.005
        assert record.workflow_run_id == "run-001"
        assert record.team_id == "team-alpha"
        assert record.provider == "openai"
        assert record.step_name == "summarize"

    def test_cost_record_defaults(self):
        record = CostRecord(
            workflow_run_id="run-002",
            step_name="extract",
            model="gpt-4o-mini",
            provider="openai",
        )
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.cost_usd == 0.0
        assert record.team_id is None
        assert record.recorded_at is not None


class TestCostTracker:
    """Verify CostTracker accumulates and queries costs."""

    @pytest.fixture
    def tracker(self):
        return CostTracker()

    @pytest.mark.asyncio
    async def test_record_adds_entry(self, tracker):
        record = CostRecord(
            workflow_run_id="run-001",
            step_name="step-1",
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.005,
            team_id="team-alpha",
        )
        await tracker.record(record)
        assert len(tracker.records) == 1

    @pytest.mark.asyncio
    async def test_get_workflow_cost(self, tracker):
        await tracker.record(CostRecord(
            workflow_run_id="run-001", step_name="s1", model="gpt-4o",
            provider="openai", input_tokens=100, output_tokens=50,
            cost_usd=0.005, team_id="team-a",
        ))
        await tracker.record(CostRecord(
            workflow_run_id="run-001", step_name="s2", model="gpt-4o",
            provider="openai", input_tokens=200, output_tokens=100,
            cost_usd=0.010, team_id="team-a",
        ))
        await tracker.record(CostRecord(
            workflow_run_id="run-002", step_name="s1", model="gpt-4o",
            provider="openai", input_tokens=50, output_tokens=25,
            cost_usd=0.002, team_id="team-a",
        ))

        wf_cost = await tracker.get_workflow_cost("run-001")
        assert abs(wf_cost - 0.015) < 1e-9

    @pytest.mark.asyncio
    async def test_get_workflow_cost_unknown_returns_zero(self, tracker):
        result = await tracker.get_workflow_cost("nonexistent")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_team_usage(self, tracker):
        await tracker.record(CostRecord(
            workflow_run_id="run-001", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=0.005, team_id="team-alpha",
        ))
        await tracker.record(CostRecord(
            workflow_run_id="run-002", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=0.010, team_id="team-alpha",
        ))
        await tracker.record(CostRecord(
            workflow_run_id="run-003", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=0.002, team_id="team-beta",
        ))

        alpha_usage = await tracker.get_team_usage("team-alpha")
        assert abs(alpha_usage - 0.015) < 1e-9

        beta_usage = await tracker.get_team_usage("team-beta")
        assert abs(beta_usage - 0.002) < 1e-9

    @pytest.mark.asyncio
    async def test_get_team_usage_unknown_returns_zero(self, tracker):
        result = await tracker.get_team_usage("nonexistent")
        assert result == 0.0


class TestBudgetStatus:
    """Verify BudgetStatus calculation via CostTracker.check_budget."""

    @pytest.fixture
    def tracker(self):
        return CostTracker()

    @pytest.mark.asyncio
    async def test_budget_under_limit(self, tracker):
        await tracker.record(CostRecord(
            workflow_run_id="run-1", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=5.0, team_id="team-x",
        ))
        status = await tracker.check_budget("team-x", budget_limit=10.0)
        assert isinstance(status, BudgetStatus)
        assert status.remaining_usd == pytest.approx(5.0)
        assert status.usage_pct == pytest.approx(50.0)
        assert status.alert == BudgetAlert.NONE

    @pytest.mark.asyncio
    async def test_budget_at_warning_threshold(self, tracker):
        """80%+ usage triggers WARNING alert."""
        await tracker.record(CostRecord(
            workflow_run_id="run-1", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=8.5, team_id="team-x",
        ))
        status = await tracker.check_budget("team-x", budget_limit=10.0)
        assert status.usage_pct == pytest.approx(85.0)
        assert status.alert == BudgetAlert.WARNING

    @pytest.mark.asyncio
    async def test_budget_below_warning_threshold(self, tracker):
        """Below 80% should be NONE alert."""
        await tracker.record(CostRecord(
            workflow_run_id="run-1", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=7.0, team_id="team-x",
        ))
        status = await tracker.check_budget("team-x", budget_limit=10.0)
        assert status.usage_pct == pytest.approx(70.0)
        assert status.alert == BudgetAlert.NONE

    @pytest.mark.asyncio
    async def test_budget_exceeded(self, tracker):
        await tracker.record(CostRecord(
            workflow_run_id="run-1", step_name="s1", model="gpt-4o",
            provider="openai", cost_usd=12.0, team_id="team-x",
        ))
        status = await tracker.check_budget("team-x", budget_limit=10.0)
        assert status.remaining_usd == pytest.approx(0.0)
        assert status.usage_pct == pytest.approx(120.0)
        assert status.alert == BudgetAlert.EXCEEDED

    @pytest.mark.asyncio
    async def test_budget_zero_limit(self, tracker):
        """Zero budget with zero usage: no alert, 0% usage."""
        status = await tracker.check_budget("team-x", budget_limit=0.0)
        assert status.remaining_usd == pytest.approx(0.0)
        assert status.usage_pct == pytest.approx(0.0)
        assert status.alert == BudgetAlert.NONE
