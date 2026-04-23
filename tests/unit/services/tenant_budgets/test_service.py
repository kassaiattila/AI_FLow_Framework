"""
@test_registry:
    suite: core-unit
    component: services.tenant_budgets.service
    covers:
        - src/aiflow/services/tenant_budgets/service.py
    phase: v1.4.10
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [unit, services, tenant_budgets, async, sprint_n, s121]
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aiflow.services.tenant_budgets import (
    TenantBudget,
    TenantBudgetService,
)


class _FakeCostRepo:
    """Records ``aggregate_running_cost`` calls and returns a fixed value."""

    def __init__(self, running_cost: float = 0.0) -> None:
        self.running_cost = running_cost
        self.calls: list[tuple[str, int]] = []

    async def aggregate_running_cost(self, tenant_id: str, window_h: int) -> float:
        self.calls.append((tenant_id, window_h))
        return self.running_cost


def _service(running_cost: float = 0.0) -> tuple[TenantBudgetService, _FakeCostRepo]:
    # Pool isn't touched when we stub `get` / `delete` per test.
    pool = object()
    repo = _FakeCostRepo(running_cost=running_cost)
    svc = TenantBudgetService(pool=pool, cost_repo=repo)  # type: ignore[arg-type]
    return svc, repo


@pytest.mark.asyncio
async def test_get_remaining_returns_none_on_missing_budget():
    svc, repo = _service(running_cost=12.5)
    svc.get = AsyncMock(return_value=None)  # type: ignore[method-assign]

    view = await svc.get_remaining("acme", "daily")

    assert view is None
    # aggregate must NOT be consulted when no budget row exists.
    assert repo.calls == []


@pytest.mark.asyncio
async def test_get_remaining_daily_uses_24h_window():
    budget = TenantBudget(tenant_id="acme", period="daily", limit_usd=100.0)
    svc, repo = _service(running_cost=30.0)
    svc.get = AsyncMock(return_value=budget)  # type: ignore[method-assign]

    view = await svc.get_remaining("acme", "daily")

    assert view is not None
    assert view.limit_usd == 100.0
    assert view.used_usd == 30.0
    assert view.remaining_usd == 70.0
    assert view.usage_pct == 30.0
    assert view.over_thresholds == []
    assert repo.calls == [("acme", 24)]


@pytest.mark.asyncio
async def test_get_remaining_monthly_uses_720h_window():
    budget = TenantBudget(tenant_id="acme", period="monthly", limit_usd=1000.0)
    svc, repo = _service(running_cost=550.0)
    svc.get = AsyncMock(return_value=budget)  # type: ignore[method-assign]

    view = await svc.get_remaining("acme", "monthly")

    assert view is not None
    assert repo.calls == [("acme", 24 * 30)]
    assert view.usage_pct == 55.0
    # default thresholds [50, 80, 95] — only 50 crossed at 55%.
    assert view.over_thresholds == [50]


@pytest.mark.asyncio
async def test_get_remaining_crosses_all_thresholds_on_breach():
    budget = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=100.0,
        alert_threshold_pct=[50, 80, 95],
    )
    svc, _ = _service(running_cost=120.0)
    svc.get = AsyncMock(return_value=budget)  # type: ignore[method-assign]

    view = await svc.get_remaining("acme", "daily")

    assert view is not None
    assert view.remaining_usd == -20.0
    assert view.usage_pct == 120.0
    assert view.over_thresholds == [50, 80, 95]


@pytest.mark.asyncio
async def test_get_remaining_custom_thresholds_only_reports_crossed():
    budget = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=200.0,
        alert_threshold_pct=[25, 75],
    )
    svc, _ = _service(running_cost=60.0)  # 30% usage
    svc.get = AsyncMock(return_value=budget)  # type: ignore[method-assign]

    view = await svc.get_remaining("acme", "daily")

    assert view is not None
    assert view.usage_pct == 30.0
    assert view.over_thresholds == [25]


@pytest.mark.asyncio
async def test_get_remaining_disabled_flag_surfaces_in_view():
    budget = TenantBudget(
        tenant_id="acme",
        period="daily",
        limit_usd=100.0,
        enabled=False,
    )
    svc, _ = _service(running_cost=10.0)
    svc.get = AsyncMock(return_value=budget)  # type: ignore[method-assign]

    view = await svc.get_remaining("acme", "daily")

    assert view is not None
    assert view.enabled is False
