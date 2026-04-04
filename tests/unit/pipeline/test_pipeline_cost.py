"""
@test_registry:
    suite: pipeline-unit
    component: api.pipelines.estimate_cost
    covers: [src/aiflow/api/v1/pipelines.py]
    phase: S12
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, cost, estimation]
"""

from __future__ import annotations

from aiflow.api.v1.pipelines import (
    _MODEL_COSTS,
    _STEP_TOKEN_ESTIMATES,
    PipelineCostEstimateResponse,
    PipelineCostStepEstimate,
)


class TestPipelineCostEstimation:
    """Tests for pipeline cost estimation models and constants."""

    def test_model_costs_has_common_models(self):
        """Cost table includes common models."""
        assert "openai/gpt-4o" in _MODEL_COSTS
        assert "openai/gpt-4o-mini" in _MODEL_COSTS
        assert _MODEL_COSTS["openai/gpt-4o-mini"] < _MODEL_COSTS["openai/gpt-4o"]

    def test_step_estimates_has_common_methods(self):
        """Token estimate table includes common step methods."""
        assert "classify" in _STEP_TOKEN_ESTIMATES
        assert "extract" in _STEP_TOKEN_ESTIMATES
        assert _STEP_TOKEN_ESTIMATES["parse"] == 0  # no LLM
        assert _STEP_TOKEN_ESTIMATES["extract"] > 0  # uses LLM

    def test_step_estimate_model(self):
        """PipelineCostStepEstimate serializes correctly."""
        step = PipelineCostStepEstimate(
            step_name="extract_data",
            service="document_extractor",
            method="extract",
            estimated_tokens=3000,
            estimated_cost_usd=0.0009,
        )
        d = step.model_dump()
        assert d["step_name"] == "extract_data"
        assert d["estimated_tokens"] == 3000

    def test_response_model_no_warning(self):
        """Response without budget warning."""
        resp = PipelineCostEstimateResponse(
            pipeline_id="p1",
            pipeline_name="invoice_processing",
            total_estimated_tokens=5000,
            total_estimated_cost_usd=0.0015,
            model="openai/gpt-4o-mini",
        )
        assert resp.budget_warning is None
        assert resp.source == "backend"

    def test_response_model_with_warning(self):
        """Response with budget warning."""
        resp = PipelineCostEstimateResponse(
            pipeline_id="p2",
            pipeline_name="expensive_pipeline",
            total_estimated_tokens=100000,
            total_estimated_cost_usd=0.75,
            model="openai/gpt-4o",
            budget_warning="WARNING: 85% of budget",
        )
        assert resp.budget_warning is not None
        assert "WARNING" in resp.budget_warning

    def test_cost_calculation_math(self):
        """Verify cost calculation: tokens * cost_per_1M / 1_000_000."""
        tokens = 3000
        cost_per_1m = _MODEL_COSTS["openai/gpt-4o-mini"]
        expected = tokens * cost_per_1m / 1_000_000
        assert abs(expected - 0.0009) < 0.0001
