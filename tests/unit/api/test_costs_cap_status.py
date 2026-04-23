"""
@test_registry:
    suite: core-unit
    component: api.v1.costs.cost_cap_status
    covers: [src/aiflow/api/v1/costs.py]
    phase: v1.4.8
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [api, costs, cost_cap, async, sprint_l, s112]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiflow.api.v1.costs import cost_cap_status


def _patch_repo(running_cost: float):
    """Stub out ``CostAttributionRepository.aggregate_running_cost``."""
    pool = MagicMock()
    get_pool = patch("aiflow.api.v1.costs.get_pool", new=AsyncMock(return_value=pool))
    repo_cls = patch("aiflow.api.v1.costs.CostAttributionRepository")
    return get_pool, repo_cls, running_cost


@pytest.mark.asyncio
async def test_cap_status_ok_under_50pct():
    get_pool, repo_cls_patch, running = _patch_repo(0.1)
    with get_pool, repo_cls_patch as repo_cls:
        repo_cls.return_value.aggregate_running_cost = AsyncMock(return_value=running)
        res = await cost_cap_status(tenant_id="acme", cap_usd=1.0, window_h=1)
    assert res.current_usd == 0.1
    assert res.utilization_pct == 10.0
    assert res.breached is False
    assert res.alert_level == "ok"


@pytest.mark.asyncio
async def test_cap_status_warning_50_to_80():
    get_pool, repo_cls_patch, running = _patch_repo(0.6)
    with get_pool, repo_cls_patch as repo_cls:
        repo_cls.return_value.aggregate_running_cost = AsyncMock(return_value=running)
        res = await cost_cap_status(tenant_id="acme", cap_usd=1.0, window_h=1)
    assert res.utilization_pct == 60.0
    assert res.alert_level == "warning"
    assert res.breached is False


@pytest.mark.asyncio
async def test_cap_status_critical_at_80pct():
    get_pool, repo_cls_patch, running = _patch_repo(0.85)
    with get_pool, repo_cls_patch as repo_cls:
        repo_cls.return_value.aggregate_running_cost = AsyncMock(return_value=running)
        res = await cost_cap_status(tenant_id="acme", cap_usd=1.0, window_h=1)
    assert res.alert_level == "critical"
    assert res.breached is False


@pytest.mark.asyncio
async def test_cap_status_breached_at_cap():
    get_pool, repo_cls_patch, running = _patch_repo(1.0)
    with get_pool, repo_cls_patch as repo_cls:
        repo_cls.return_value.aggregate_running_cost = AsyncMock(return_value=running)
        res = await cost_cap_status(tenant_id="acme", cap_usd=1.0, window_h=1)
    assert res.breached is True
    assert res.alert_level == "exceeded"


@pytest.mark.asyncio
async def test_cap_status_no_cap_returns_ok():
    """When cap_usd is None (default) → alert stays ok regardless of spend."""
    get_pool, repo_cls_patch, running = _patch_repo(100.0)
    with get_pool, repo_cls_patch as repo_cls:
        repo_cls.return_value.aggregate_running_cost = AsyncMock(return_value=running)
        res = await cost_cap_status(tenant_id="acme", cap_usd=None, window_h=1)
    # cap_usd=None → no breach evaluation even at $100 spent
    assert res.breached is False
    assert res.alert_level == "ok"
    assert res.utilization_pct == 0.0


@pytest.mark.asyncio
async def test_cap_status_zero_cap_guard():
    """cap_usd=0 is treated as 'no cap' to avoid div-by-zero."""
    get_pool, repo_cls_patch, running = _patch_repo(5.0)
    with get_pool, repo_cls_patch as repo_cls:
        repo_cls.return_value.aggregate_running_cost = AsyncMock(return_value=running)
        res = await cost_cap_status(tenant_id="acme", cap_usd=0.0, window_h=1)
    assert res.utilization_pct == 0.0
    assert res.alert_level == "ok"


@pytest.mark.asyncio
async def test_cap_status_db_failure_returns_zero_current():
    """DB errors are swallowed — endpoint still returns a CostCapStatus."""
    with (
        patch("aiflow.api.v1.costs.get_pool", new=AsyncMock(side_effect=RuntimeError("pg down"))),
    ):
        res = await cost_cap_status(tenant_id="acme", cap_usd=1.0, window_h=1)
    assert res.current_usd == 0.0
    assert res.breached is False
