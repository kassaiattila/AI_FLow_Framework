"""
@test_registry:
    suite: core-unit
    component: guardrails.cost_estimator
    covers:
        - src/aiflow/guardrails/cost_estimator.py
    phase: v1.4.10
    priority: high
    estimated_duration_ms: 50
    requires_services: []
    tags: [unit, guardrails, cost_preflight, sprint_n, s122]
"""

from __future__ import annotations

import pytest

from aiflow.guardrails.cost_estimator import (
    PER_TIER_FALLBACK_USD_PER_1K_IN,
    PER_TIER_FALLBACK_USD_PER_1K_OUT,
    CostEstimator,
    _tier_for_model,
)


class TestCostEstimator:
    def test_known_model_uses_litellm_pricing(self):
        """gpt-4o-mini is in the litellm table — result must be positive and
        shaped like (input_rate*in_tokens + output_rate*out_tokens)."""
        est = CostEstimator()
        projected = est.estimate(model="gpt-4o-mini", input_tokens=1000, max_output_tokens=100)
        assert projected > 0.0
        # Sanity: cost for 1k prompt + 100 completion is well under $0.01 on gpt-4o-mini.
        assert projected < 0.01

    def test_unknown_model_falls_back_to_per_tier_ceiling(self, caplog):
        """An entirely unknown model string lands in the fallback branch and
        the cost equals the per-tier ceiling math exactly."""
        est = CostEstimator()
        projected = est.estimate(
            model="totally-made-up-provider/unknown-model-x",
            input_tokens=1000,
            max_output_tokens=500,
        )
        # "unknown-model-x" has no premium/cheap keywords → standard tier.
        in_rate = PER_TIER_FALLBACK_USD_PER_1K_IN["standard"]
        out_rate = PER_TIER_FALLBACK_USD_PER_1K_OUT["standard"]
        expected = 1.0 * in_rate + 0.5 * out_rate
        assert projected == pytest.approx(expected)

    def test_zero_tokens_yields_zero_or_tiny_cost(self):
        est = CostEstimator()
        projected = est.estimate(model="gpt-4o-mini", input_tokens=0, max_output_tokens=0)
        assert projected >= 0.0

    def test_negative_token_counts_clamped_to_zero(self):
        est = CostEstimator()
        projected = est.estimate(
            model="totally-made-up/unknown",
            input_tokens=-5,
            max_output_tokens=-10,
        )
        assert projected == 0.0


class TestTierRouting:
    @pytest.mark.parametrize(
        "model,expected_tier",
        [
            ("openai/gpt-4o", "premium"),
            ("anthropic/claude-3-opus-20240229", "premium"),
            ("openai/gpt-4o-mini", "cheap"),
            ("anthropic/claude-3-5-haiku", "cheap"),
            ("google/gemini-1.5-flash", "cheap"),
            ("mistral/mistral-large", "standard"),
        ],
    )
    def test_tier_classification(self, model: str, expected_tier: str) -> None:
        assert _tier_for_model(model) == expected_tier
