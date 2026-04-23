"""
@test_registry:
    suite: core-unit
    component: services.tenant_budgets.contracts
    covers: [src/aiflow/services/tenant_budgets/contracts.py]
    phase: v1.4.10
    priority: high
    estimated_duration_ms: 50
    requires_services: []
    tags: [unit, services, tenant_budgets, sprint_n, s121]
"""

from __future__ import annotations

import pytest

from aiflow.services.tenant_budgets.contracts import (
    BudgetView,
    TenantBudget,
)


def test_tenant_budget_sorts_and_dedupes_thresholds():
    b = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=100.0,
        alert_threshold_pct=[95, 50, 80, 50],
    )
    assert b.alert_threshold_pct == [50, 80, 95]


def test_tenant_budget_rejects_out_of_range_threshold():
    with pytest.raises(ValueError, match=r"\[1, 100\]"):
        TenantBudget(
            tenant_id="acme",
            period="daily",
            limit_usd=100.0,
            alert_threshold_pct=[50, 120],
        )


def test_tenant_budget_rejects_zero_threshold():
    with pytest.raises(ValueError, match=r"\[1, 100\]"):
        TenantBudget(
            tenant_id="acme",
            period="daily",
            limit_usd=100.0,
            alert_threshold_pct=[0, 50],
        )


def test_tenant_budget_rejects_negative_limit():
    with pytest.raises(ValueError):
        TenantBudget(
            tenant_id="acme",
            period="daily",
            limit_usd=-0.01,
        )


def test_tenant_budget_rejects_invalid_period():
    with pytest.raises(ValueError):
        TenantBudget(
            tenant_id="acme",
            period="weekly",  # type: ignore[arg-type]
            limit_usd=1.0,
        )


def test_budget_view_from_budget_math_under_threshold():
    b = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=100.0,
        alert_threshold_pct=[50, 80, 95],
    )
    v = BudgetView.from_budget(b, used_usd=30.0)
    assert v.used_usd == 30.0
    assert v.remaining_usd == 70.0
    assert v.usage_pct == 30.0
    assert v.over_thresholds == []


def test_budget_view_from_budget_crosses_two_thresholds():
    b = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=100.0,
        alert_threshold_pct=[50, 80, 95],
    )
    v = BudgetView.from_budget(b, used_usd=85.0)
    assert v.usage_pct == 85.0
    assert v.over_thresholds == [50, 80]


def test_budget_view_from_budget_at_100_percent_crosses_all():
    b = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=100.0,
        alert_threshold_pct=[50, 80, 95],
    )
    v = BudgetView.from_budget(b, used_usd=150.0)
    assert v.usage_pct == 150.0
    assert v.remaining_usd == -50.0
    assert v.over_thresholds == [50, 80, 95]


def test_budget_view_zero_limit_yields_zero_usage_pct():
    """A zero-limit budget must not divide by zero."""
    b = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=0.0,
        alert_threshold_pct=[50, 80, 95],
    )
    v = BudgetView.from_budget(b, used_usd=5.0)
    assert v.usage_pct == 0.0
    assert v.over_thresholds == []


def test_budget_view_clamps_negative_used_usd_to_zero():
    b = TenantBudget(tenant_id="acme", period="daily", limit_usd=100.0)
    v = BudgetView.from_budget(b, used_usd=-10.0)
    assert v.used_usd == 0.0
    assert v.remaining_usd == 100.0
