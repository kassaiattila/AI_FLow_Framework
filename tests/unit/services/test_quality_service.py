"""
@test_registry:
    suite: service-unit
    component: services.quality
    covers: [src/aiflow/services/quality/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, quality, rubric, cost-estimation, evaluation]
"""

from __future__ import annotations

import pytest

from aiflow.services.quality.service import QualityConfig, QualityService


@pytest.fixture()
def svc() -> QualityService:
    return QualityService(config=QualityConfig())


class TestQualityService:
    @pytest.mark.asyncio
    async def test_get_overview(self, svc: QualityService) -> None:
        """get_overview returns QualityOverview with correct aggregation."""
        # First evaluate a rubric so overview has data
        await svc.evaluate_rubric(
            actual="This is a well-structured response with details.",
            rubric="relevance",
        )
        overview = await svc.get_overview()
        assert overview.total_evaluations == 1
        assert overview.avg_score > 0
        assert 0.0 <= overview.pass_rate <= 1.0

    @pytest.mark.asyncio
    async def test_estimate_pipeline_cost(self, svc: QualityService) -> None:
        """estimate_pipeline_cost returns CostEstimate with tokens and cost."""
        steps = [
            {"method": "classify"},
            {"method": "extract"},
            {"method": "chunk"},
        ]
        estimate = await svc.estimate_pipeline_cost(steps)
        assert estimate.estimated_tokens > 0
        assert estimate.estimated_cost_usd > 0
        assert estimate.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_list_rubrics(self, svc: QualityService) -> None:
        """list_rubrics returns non-empty dict of built-in rubrics."""
        rubrics = svc.list_rubrics()
        assert isinstance(rubrics, dict)
        assert len(rubrics) > 0
        assert "relevance" in rubrics
        assert "faithfulness" in rubrics

    @pytest.mark.asyncio
    async def test_evaluate_rubric_no_llm(self, svc: QualityService) -> None:
        """evaluate_rubric uses heuristic scoring without LLM."""
        result = await svc.evaluate_rubric(
            actual="The answer covers all key aspects of the question comprehensively.",
            rubric="completeness",
            expected="The answer should cover all key aspects.",
        )
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.pass_, bool)
        assert result.rubric == "completeness"
        assert result.reasoning != ""

    @pytest.mark.asyncio
    async def test_health_check(self, svc: QualityService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
