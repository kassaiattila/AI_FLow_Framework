"""
@test_registry:
    suite: core-unit
    component: core.config (CostSettings umbrella)
    covers:
        - src/aiflow/core/config.py (CostSettings, BudgetSettings, CostGuardrailSettings)
    phase: v1.5.4
    priority: high
    estimated_duration_ms: 60
    requires_services: []
    tags: [unit, core, config, sprint_u, s154, sn_fu]
"""

from __future__ import annotations

import pytest

from aiflow.core.config import (
    AIFlowSettings,
    BudgetSettings,
    CostGuardrailSettings,
    CostSettings,
)


class TestCostSettingsUmbrella:
    """Sprint U S154 (SN-FU) — CostSettings consolidates budget + guardrail."""

    def test_umbrella_has_budget_and_guardrail_subfields(self):
        """CostSettings exposes `budget` and `guardrail` nested instances."""
        cost = CostSettings()
        assert isinstance(cost.budget, BudgetSettings)
        assert isinstance(cost.guardrail, CostGuardrailSettings)

    def test_umbrella_defaults_match_legacy_defaults(self):
        """Umbrella nested defaults match the legacy direct-on-Settings defaults."""
        s = AIFlowSettings()

        # Budget default
        assert s.cost.budget.default_per_run_usd == s.budget.default_per_run_usd == 10.0
        assert s.cost.budget.alert_threshold_pct == s.budget.alert_threshold_pct == 80

        # Guardrail default
        assert s.cost.guardrail.enabled is False
        assert s.cost_guardrail.enabled is False
        assert s.cost.guardrail.dry_run is True
        assert s.cost_guardrail.dry_run is True

    def test_legacy_aliases_still_present_on_settings(self):
        """Backward-compat: settings.budget and settings.cost_guardrail keep working."""
        s = AIFlowSettings()
        # Both forms should resolve cleanly
        assert s.budget is not None
        assert s.cost_guardrail is not None
        assert s.cost is not None

    def test_legacy_env_prefix_still_reads_budget(self, monkeypatch):
        """AIFLOW_BUDGET__DEFAULT_PER_RUN_USD continues to work."""
        monkeypatch.setenv("AIFLOW_BUDGET__DEFAULT_PER_RUN_USD", "42.5")
        # Re-instantiate (singleton bypassed)
        b = BudgetSettings()
        assert b.default_per_run_usd == 42.5

    def test_legacy_env_prefix_still_reads_guardrail(self, monkeypatch):
        """AIFLOW_COST_GUARDRAIL__ENABLED continues to work."""
        monkeypatch.setenv("AIFLOW_COST_GUARDRAIL__ENABLED", "true")
        g = CostGuardrailSettings()
        assert g.enabled is True

    def test_tier_fallback_dicts_have_all_three_tiers(self):
        """Sprint U S154 (SN-FU-2): default tier_fallback dicts cover premium/standard/cheap."""
        g = CostGuardrailSettings()
        assert set(g.tier_fallback_in_per_1k.keys()) == {"premium", "standard", "cheap"}
        assert set(g.tier_fallback_out_per_1k.keys()) == {"premium", "standard", "cheap"}
        # Default values match Sprint N module constants
        assert g.tier_fallback_in_per_1k["standard"] == pytest.approx(0.01)
        assert g.tier_fallback_out_per_1k["premium"] == pytest.approx(0.06)

    def test_tier_fallback_env_override_via_json(self, monkeypatch):
        """Operator can override tier_fallback_*_per_1k via JSON env value."""
        monkeypatch.setenv(
            "AIFLOW_COST_GUARDRAIL__TIER_FALLBACK_IN_PER_1K",
            '{"premium": 0.05, "standard": 0.02, "cheap": 0.005}',
        )
        g = CostGuardrailSettings()
        assert g.tier_fallback_in_per_1k["premium"] == 0.05
        assert g.tier_fallback_in_per_1k["standard"] == 0.02
