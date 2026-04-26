"""
@test_registry:
    suite: core-unit
    component: guardrails.cost_preflight
    covers:
        - src/aiflow/guardrails/cost_preflight.py (CostPreflightGuardrail.check_step)
    phase: v1.5.4
    priority: high
    estimated_duration_ms: 80
    requires_services: []
    tags: [unit, guardrails, cost_preflight, sprint_u, s154, st_fu_3]
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiflow.guardrails.cost_estimator import CostEstimator
from aiflow.guardrails.cost_preflight import CostPreflightGuardrail


def _guardrail(*, enabled: bool, dry_run: bool) -> CostPreflightGuardrail:
    """Construct a guardrail with a deterministic estimator (fixed standard tier rates)."""
    estimator = CostEstimator(
        tier_fallback_in_per_1k={"standard": 0.01, "premium": 0.03, "cheap": 0.001},
        tier_fallback_out_per_1k={"standard": 0.02, "premium": 0.06, "cheap": 0.002},
    )
    return CostPreflightGuardrail(
        budgets=MagicMock(),
        estimator=estimator,
        enabled=enabled,
        dry_run=dry_run,
    )


class TestCheckStep:
    """Sprint U S154 (ST-FU-3) — per-step cost ceiling consolidation."""

    def test_no_ceiling_skips_check(self):
        """ceiling_usd=None → allowed, reason='step_no_ceiling', no projection."""
        g = _guardrail(enabled=True, dry_run=False)
        d = g.check_step(
            step_name="extract",
            model="gpt-4o-mini",
            input_tokens=1000,
            max_output_tokens=500,
            ceiling_usd=None,
        )
        assert d.allowed is True
        assert d.reason == "step_no_ceiling"
        assert d.projected_usd == 0.0

    def test_disabled_guardrail_skips(self):
        """guardrail enabled=False → allowed, reason='disabled', no projection."""
        g = _guardrail(enabled=False, dry_run=True)
        d = g.check_step(
            step_name="extract",
            model="gpt-4o-mini",
            input_tokens=1000,
            max_output_tokens=500,
            ceiling_usd=0.01,
        )
        assert d.allowed is True
        assert d.reason == "disabled"

    def test_under_ceiling_allows(self):
        """projected ≤ ceiling → allowed, reason='step_under_ceiling'."""
        g = _guardrail(enabled=True, dry_run=False)
        d = g.check_step(
            step_name="extract_header",
            model="unknown-llama",  # forces standard-tier fallback (deterministic)
            input_tokens=1000,
            max_output_tokens=500,
            ceiling_usd=1.0,
        )
        assert d.allowed is True
        assert d.reason == "step_under_ceiling"
        # 1*0.01 + 0.5*0.02 = 0.020 (well under 1.0)
        assert d.projected_usd == pytest.approx(0.020, rel=1e-6)
        assert d.remaining_usd == 1.0  # ceiling reflected

    def test_over_ceiling_dry_run_allows_with_warning(self):
        """projected > ceiling AND dry_run=True → allowed, reason='step_dry_run_over_ceiling'."""
        g = _guardrail(enabled=True, dry_run=True)
        d = g.check_step(
            step_name="extract_lines",
            model="unknown-llama",
            input_tokens=1000,
            max_output_tokens=500,
            ceiling_usd=0.001,  # tiny ceiling, projected (0.020) busts it
        )
        assert d.allowed is True
        assert d.reason == "step_dry_run_over_ceiling"
        assert d.projected_usd == pytest.approx(0.020, rel=1e-6)
        assert d.dry_run is True

    def test_over_ceiling_enforced_refuses(self):
        """projected > ceiling AND dry_run=False → allowed=False, reason='step_over_ceiling'."""
        g = _guardrail(enabled=True, dry_run=False)
        d = g.check_step(
            step_name="extract_lines",
            model="unknown-llama",
            input_tokens=1000,
            max_output_tokens=500,
            ceiling_usd=0.001,
        )
        assert d.allowed is False
        assert d.reason == "step_over_ceiling"
        assert d.projected_usd == pytest.approx(0.020, rel=1e-6)
        assert d.dry_run is False

    def test_check_step_is_synchronous(self):
        """check_step is sync (not async) — caller doesn't need to await it."""
        g = _guardrail(enabled=True, dry_run=False)
        # Direct call without await must work
        d = g.check_step(
            step_name="x",
            model="m",
            input_tokens=10,
            max_output_tokens=5,
            ceiling_usd=10.0,
        )
        assert d.allowed is True
