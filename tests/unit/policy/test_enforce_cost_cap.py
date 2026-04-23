"""
@test_registry:
    suite: core-unit
    component: policy.engine.enforce_cost_cap
    covers: [src/aiflow/policy/engine.py]
    phase: v1.4.8
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [policy, cost_cap, async, sprint_l, s112]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiflow.core.errors import CostCapBreached
from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine


class TestEnforceCostCap:
    @pytest.mark.asyncio
    async def test_returns_zero_when_cap_not_configured(self):
        engine = PolicyEngine(profile_config=PolicyConfig())
        result = await engine.enforce_cost_cap(tenant_id="acme", pool=MagicMock())
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_passes_when_current_below_cap(self):
        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=1.0, cost_cap_window_h=1),
        )
        with patch("aiflow.policy.engine.CostAttributionRepository") as repo_cls:
            repo = repo_cls.return_value
            repo.aggregate_running_cost = AsyncMock(return_value=0.25)
            result = await engine.enforce_cost_cap(tenant_id="acme", pool=MagicMock())
        assert result == 0.25

    @pytest.mark.asyncio
    async def test_raises_when_current_at_cap(self):
        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=1.0, cost_cap_window_h=1),
        )
        with patch("aiflow.policy.engine.CostAttributionRepository") as repo_cls:
            repo = repo_cls.return_value
            repo.aggregate_running_cost = AsyncMock(return_value=1.0)
            with pytest.raises(CostCapBreached) as exc:
                await engine.enforce_cost_cap(tenant_id="acme", pool=MagicMock())
        assert exc.value.tenant_id == "acme"
        assert exc.value.cap_usd == 1.0
        assert exc.value.current_usd == 1.0
        assert exc.value.window_h == 1
        assert exc.value.http_status == 429
        assert exc.value.error_code == "COST_CAP_BREACHED"

    @pytest.mark.asyncio
    async def test_raises_when_current_exceeds_cap(self):
        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=0.5, cost_cap_window_h=24),
        )
        with patch("aiflow.policy.engine.CostAttributionRepository") as repo_cls:
            repo = repo_cls.return_value
            repo.aggregate_running_cost = AsyncMock(return_value=1.75)
            with pytest.raises(CostCapBreached) as exc:
                await engine.enforce_cost_cap(tenant_id="tenant-42", pool=MagicMock())
        assert exc.value.current_usd == 1.75
        assert exc.value.window_h == 24
        assert exc.value.details["tenant_id"] == "tenant-42"

    @pytest.mark.asyncio
    async def test_uses_tenant_override_cap(self):
        """Tenant-specific cap beats profile default."""
        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=10.0, cost_cap_window_h=1),
            tenant_overrides={"strict-tenant": {"cost_cap_usd": 0.1}},
        )
        with patch("aiflow.policy.engine.CostAttributionRepository") as repo_cls:
            repo = repo_cls.return_value
            repo.aggregate_running_cost = AsyncMock(return_value=0.5)
            with pytest.raises(CostCapBreached) as exc:
                await engine.enforce_cost_cap(tenant_id="strict-tenant", pool=MagicMock())
        assert exc.value.cap_usd == 0.1


class TestPolicyEngineGetForInstance:
    """Instance-level override merge — layered over tenant + profile defaults."""

    def test_returns_tenant_config_when_no_instance_override(self):
        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=5.0),
            tenant_overrides={"acme": {"cost_cap_usd": 2.0}},
        )
        cfg = engine.get_for_instance(tenant_id="acme")
        assert cfg.cost_cap_usd == 2.0

    def test_empty_instance_override_falls_through(self):
        engine = PolicyEngine(profile_config=PolicyConfig(cost_cap_usd=5.0))
        cfg = engine.get_for_instance(tenant_id="acme", instance_override={})
        assert cfg.cost_cap_usd == 5.0

    def test_instance_override_wins_over_tenant(self):
        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=10.0, cost_cap_window_h=1),
            tenant_overrides={"acme": {"cost_cap_usd": 2.0}},
        )
        cfg = engine.get_for_instance(
            tenant_id="acme",
            instance_override={"cost_cap_usd": 0.1},
        )
        assert cfg.cost_cap_usd == 0.1
        # window_h inherited from profile (no override at tenant or instance)
        assert cfg.cost_cap_window_h == 1

    def test_instance_override_for_unknown_tenant(self):
        """Unknown tenant → profile defaults + instance override."""
        engine = PolicyEngine(profile_config=PolicyConfig(cost_cap_usd=5.0))
        cfg = engine.get_for_instance(
            tenant_id="ghost",
            instance_override={"cost_cap_usd": 1.0},
        )
        assert cfg.cost_cap_usd == 1.0


class TestCostCapBreachedError:
    """Structured details + HTTP class-vars on ``CostCapBreached``."""

    def test_details_carry_all_fields(self):
        err = CostCapBreached(
            tenant_id="acme",
            cap_usd=1.0,
            current_usd=1.5,
            window_h=24,
        )
        assert err.details == {
            "tenant_id": "acme",
            "cap_usd": 1.0,
            "current_usd": 1.5,
            "window_h": 24,
        }
        assert err.error_code == "COST_CAP_BREACHED"
        assert err.http_status == 429

    def test_message_includes_tenant_and_costs(self):
        err = CostCapBreached(
            tenant_id="acme",
            cap_usd=0.001,
            current_usd=0.0012,
            window_h=1,
        )
        msg = str(err)
        assert "acme" in msg
        assert "0.001" in msg or "0.0010" in msg
