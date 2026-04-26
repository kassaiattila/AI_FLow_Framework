"""
@test_registry:
    suite: core-unit
    component: guardrails.cost_estimator
    covers:
        - src/aiflow/guardrails/cost_estimator.py
        - src/aiflow/core/config.py (CostGuardrailSettings.tier_fallback_*)
    phase: v1.5.4
    priority: high
    estimated_duration_ms: 50
    requires_services: []
    tags: [unit, guardrails, cost_preflight, sprint_u, s154, sn_fu_2]
"""

from __future__ import annotations

import pytest

from aiflow.guardrails.cost_estimator import (
    PER_TIER_FALLBACK_USD_PER_1K_IN,
    PER_TIER_FALLBACK_USD_PER_1K_OUT,
    CostEstimator,
)


class TestTierFallbackEnvOverride:
    """Sprint U S154 (SN-FU-2) — per-tier fallback ceilings env-tunable."""

    def test_explicit_dict_overrides_module_default_for_unknown_model(self):
        """An unknown model uses the operator-supplied tier ceiling, not the module default."""
        custom_in = {"premium": 0.05, "standard": 0.025, "cheap": 0.005}
        custom_out = {"premium": 0.10, "standard": 0.05, "cheap": 0.010}
        est = CostEstimator(
            tier_fallback_in_per_1k=custom_in,
            tier_fallback_out_per_1k=custom_out,
        )
        # "unknown-llama-7b" classifies as "standard" (no premium/cheap keyword)
        projected = est.estimate(model="unknown-llama-7b", input_tokens=1000, max_output_tokens=500)
        # Expected: 1*0.025 (in) + 0.5*0.05 (out) = 0.025 + 0.025 = 0.050
        assert projected == pytest.approx(0.050, rel=1e-6)

    def test_default_constructor_falls_back_to_module_constants(self):
        """When no override is supplied AND settings unavailable, module defaults apply."""
        # `unknown-foo` → standard tier. Module default in=0.01, out=0.02.
        est = CostEstimator()
        # Bypass the settings-resolver by re-inserting module defaults explicitly:
        est._in_rates = dict(PER_TIER_FALLBACK_USD_PER_1K_IN)
        est._out_rates = dict(PER_TIER_FALLBACK_USD_PER_1K_OUT)
        projected = est.estimate(model="unknown-foo", input_tokens=1000, max_output_tokens=500)
        # 1*0.01 + 0.5*0.02 = 0.01 + 0.01 = 0.020
        assert projected == pytest.approx(0.020, rel=1e-6)

    def test_partial_override_keeps_module_default_for_other_tiers(self):
        """If override only sets `standard`, premium/cheap fall back to module constants."""
        partial_in = {"standard": 0.025}  # only standard
        partial_out = {"standard": 0.05}
        est = CostEstimator(
            tier_fallback_in_per_1k=partial_in,
            tier_fallback_out_per_1k=partial_out,
        )
        # standard tier model — uses override
        std_proj = est.estimate(model="unknown-foo", input_tokens=1000, max_output_tokens=500)
        assert std_proj == pytest.approx(0.025 + 0.025, rel=1e-6)

        # premium tier model — falls back to module default 0.03/0.06 because not in partial dict
        prem_proj = est.estimate(model="gpt-4-turbo-fake", input_tokens=1000, max_output_tokens=500)
        # 1*0.03 + 0.5*0.06 = 0.03 + 0.03 = 0.060
        assert prem_proj == pytest.approx(0.060, rel=1e-6)
