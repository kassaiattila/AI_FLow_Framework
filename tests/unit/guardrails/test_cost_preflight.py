"""
@test_registry:
    suite: core-unit
    component: guardrails.cost_preflight
    covers:
        - src/aiflow/guardrails/cost_preflight.py
        - src/aiflow/core/errors.py
    phase: v1.4.10
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [unit, guardrails, cost_preflight, sprint_n, s122]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.core.errors import CostGuardrailRefused
from aiflow.guardrails.cost_estimator import CostEstimator
from aiflow.guardrails.cost_preflight import CostPreflightGuardrail, PreflightDecision
from aiflow.services.tenant_budgets.contracts import BudgetView


def _view(remaining: float, used: float = 0.0, limit: float = 10.0) -> BudgetView:
    return BudgetView(
        tenant_id="t1",
        period="daily",
        limit_usd=limit,
        used_usd=used,
        remaining_usd=remaining,
        usage_pct=100.0 * used / limit if limit else 0.0,
        alert_threshold_pct=[50, 80, 95],
        over_thresholds=[],
        enabled=True,
    )


def _fake_budgets(view: BudgetView | None) -> MagicMock:
    mock = MagicMock()
    mock.get_remaining = AsyncMock(return_value=view)
    return mock


def _fixed_estimator(value: float) -> CostEstimator:
    est = CostEstimator()
    est.estimate = MagicMock(return_value=value)  # type: ignore[method-assign]
    return est


class TestDecisionTable:
    @pytest.mark.asyncio
    async def test_disabled_short_circuits_without_io(self):
        budgets = _fake_budgets(_view(5.0))
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(99.0),
            enabled=False,
        )
        decision = await g.check(
            "t1", model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100
        )
        assert decision.allowed is True
        assert decision.reason == "disabled"
        assert decision.projected_usd == 0.0
        budgets.get_remaining.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_budget_row_is_allowed(self):
        budgets = _fake_budgets(None)
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(5.0),
            enabled=True,
            dry_run=False,
        )
        decision = await g.check(
            "t1", model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100
        )
        assert decision.allowed is True
        assert decision.reason == "no_budget"
        assert decision.remaining_usd is None
        assert decision.projected_usd == 5.0
        budgets.get_remaining.assert_awaited_once_with("t1", "daily")

    @pytest.mark.asyncio
    async def test_projected_under_remaining_is_allowed(self):
        budgets = _fake_budgets(_view(remaining=10.0))
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(1.0),
            enabled=True,
            dry_run=False,
        )
        decision = await g.check(
            "t1", model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100
        )
        assert decision.allowed is True
        assert decision.reason == "under_budget"
        assert decision.projected_usd == 1.0
        assert decision.remaining_usd == 10.0

    @pytest.mark.asyncio
    async def test_projected_equal_remaining_is_allowed(self):
        """Refusal uses strict `>`, so projected == remaining must pass."""
        budgets = _fake_budgets(_view(remaining=2.0))
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(2.0),
            enabled=True,
            dry_run=False,
        )
        decision = await g.check(
            "t1", model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100
        )
        assert decision.allowed is True
        assert decision.reason == "under_budget"

    @pytest.mark.asyncio
    async def test_projected_over_remaining_dry_run_allows(self):
        budgets = _fake_budgets(_view(remaining=1.0))
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(5.0),
            enabled=True,
            dry_run=True,
        )
        decision = await g.check(
            "t1", model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100
        )
        assert decision.allowed is True
        assert decision.reason == "dry_run_over_budget"
        assert decision.dry_run is True

    @pytest.mark.asyncio
    async def test_projected_over_remaining_enforced_refuses(self):
        budgets = _fake_budgets(_view(remaining=1.0))
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(5.0),
            enabled=True,
            dry_run=False,
        )
        decision = await g.check(
            "t1", model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100
        )
        assert decision.allowed is False
        assert decision.reason == "over_budget"
        assert decision.projected_usd == 5.0
        assert decision.remaining_usd == 1.0
        assert decision.dry_run is False

    @pytest.mark.asyncio
    async def test_period_routed_through(self):
        """Monthly period must flow through to get_remaining."""
        budgets = _fake_budgets(_view(remaining=5.0))
        g = CostPreflightGuardrail(
            budgets=budgets,
            estimator=_fixed_estimator(1.0),
            enabled=True,
            dry_run=False,
            period="monthly",
        )
        await g.check("t1", model="gpt-4o-mini", input_tokens=500, max_output_tokens=50)
        budgets.get_remaining.assert_awaited_once_with("t1", "monthly")


class TestRefusalError:
    def test_cost_guardrail_refused_shape(self):
        err = CostGuardrailRefused(
            tenant_id="acme",
            projected_usd=0.02,
            remaining_usd=0.01,
            period="daily",
            reason="over_budget",
            dry_run=False,
        )
        assert err.http_status == 429
        assert err.error_code == "COST_GUARDRAIL_REFUSED"
        assert err.is_transient is False
        # Structured details payload — exact key set required by the API layer.
        for key in (
            "refused",
            "tenant_id",
            "projected_usd",
            "remaining_usd",
            "period",
            "reason",
            "dry_run",
        ):
            assert key in err.details
        assert err.details["refused"] is True
        assert err.details["dry_run"] is False


class TestPreflightDecisionModel:
    def test_decision_is_pydantic_serializable(self):
        d = PreflightDecision(
            allowed=False,
            projected_usd=1.23,
            remaining_usd=0.5,
            reason="over_budget",
            period="daily",
            dry_run=False,
        )
        payload = d.model_dump()
        assert payload["reason"] == "over_budget"
        assert payload["period"] == "daily"
