"""
@test_registry:
    suite: service-unit
    component: services.quality
    covers: [
        src/aiflow/services/quality/service.py,
        src/aiflow/pipeline/adapters/quality_adapter.py,
    ]
    phase: C17
    priority: critical
    estimated_duration_ms: 1000
    requires_services: []
    tags: [quality, rubric, cost, evaluation, tier4]
"""

from __future__ import annotations

import pytest

from aiflow.services.quality.service import (
    BUILTIN_RUBRICS,
    CostEstimate,
    QualityConfig,
    QualityOverview,
    QualityService,
    RubricResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def quality_svc() -> QualityService:
    return QualityService(config=QualityConfig())


# ===========================================================================
# TestQualityService
# ===========================================================================


class TestQualityService:
    def test_service_name(self, quality_svc: QualityService) -> None:
        assert quality_svc.service_name == "quality"

    def test_service_description(self, quality_svc: QualityService) -> None:
        assert "quality" in quality_svc.service_description.lower()

    @pytest.mark.asyncio
    async def test_health_check(self, quality_svc: QualityService) -> None:
        result = await quality_svc.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_rubric_with_expected(
        self, quality_svc: QualityService
    ) -> None:
        """Evaluate with expected output produces token-overlap score."""
        await quality_svc.start()
        result = await quality_svc.evaluate_rubric(
            actual="The cat sat on the mat",
            rubric="relevance",
            expected="The cat sat on the mat",
        )
        assert isinstance(result, RubricResult)
        assert result.score == 1.0  # exact match
        assert result.pass_ is True
        assert result.rubric == "relevance"
        assert result.model == "gpt-4o-mini"  # default

    @pytest.mark.asyncio
    async def test_evaluate_rubric_no_expected(
        self, quality_svc: QualityService
    ) -> None:
        """Evaluate without expected output uses heuristic scoring."""
        await quality_svc.start()
        result = await quality_svc.evaluate_rubric(
            actual="This is a well-structured response with multiple sentences. "
            "It covers the topic thoroughly.\nWith multiple paragraphs.",
            rubric="completeness",
        )
        assert isinstance(result, RubricResult)
        assert 0.0 < result.score <= 1.0
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_evaluate_rubric_empty_actual(
        self, quality_svc: QualityService
    ) -> None:
        """Empty actual text scores 0."""
        await quality_svc.start()
        result = await quality_svc.evaluate_rubric(
            actual="",
            rubric="relevance",
        )
        assert result.score == 0.0
        assert result.pass_ is False

    @pytest.mark.asyncio
    async def test_evaluate_custom_rubric(
        self, quality_svc: QualityService
    ) -> None:
        """Custom rubric text (not a built-in name) is accepted."""
        await quality_svc.start()
        result = await quality_svc.evaluate_rubric(
            actual="Good response here.",
            rubric="Score based on how friendly the tone is.",
        )
        assert isinstance(result, RubricResult)
        assert result.rubric == "Score based on how friendly the tone is."

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_model(
        self, quality_svc: QualityService
    ) -> None:
        """Custom model name is stored in the result."""
        await quality_svc.start()
        result = await quality_svc.evaluate_rubric(
            actual="Hello world",
            rubric="relevance",
            model="gpt-4o",
        )
        assert result.model == "gpt-4o"

    def test_builtin_rubrics_exist(self) -> None:
        """All 6 built-in rubrics are defined."""
        expected_rubrics = [
            "relevance",
            "faithfulness",
            "completeness",
            "extraction_accuracy",
            "intent_correctness",
            "hungarian_quality",
        ]
        assert len(BUILTIN_RUBRICS) == 6
        for name in expected_rubrics:
            assert name in BUILTIN_RUBRICS, (
                f"Missing built-in rubric: {name}"
            )
            assert len(BUILTIN_RUBRICS[name]) > 20, (
                f"Rubric '{name}' description too short"
            )

    def test_list_rubrics(self, quality_svc: QualityService) -> None:
        rubrics = quality_svc.list_rubrics()
        assert isinstance(rubrics, dict)
        assert len(rubrics) == 6
        assert "relevance" in rubrics

    @pytest.mark.asyncio
    async def test_overview_defaults(
        self, quality_svc: QualityService
    ) -> None:
        """Overview with no evaluations returns zeros."""
        await quality_svc.start()
        overview = await quality_svc.get_overview()
        assert isinstance(overview, QualityOverview)
        assert overview.total_evaluations == 0
        assert overview.avg_score == 0.0
        assert overview.pass_rate == 0.0

    @pytest.mark.asyncio
    async def test_overview_after_evaluations(
        self, quality_svc: QualityService
    ) -> None:
        """Overview reflects accumulated evaluation results."""
        await quality_svc.start()

        # Two passing evaluations
        await quality_svc.evaluate_rubric(
            actual="The cat sat on the mat",
            rubric="relevance",
            expected="The cat sat on the mat",
        )
        await quality_svc.evaluate_rubric(
            actual="",
            rubric="relevance",
            expected="Something",
        )

        overview = await quality_svc.get_overview()
        assert overview.total_evaluations == 2
        assert overview.avg_score == 0.5  # (1.0 + 0.0) / 2
        assert overview.pass_rate == 0.5  # 1 out of 2 pass

    @pytest.mark.asyncio
    async def test_estimate_cost(
        self, quality_svc: QualityService
    ) -> None:
        """Cost estimation returns positive values for pipeline steps."""
        await quality_svc.start()
        steps = [
            {"service": "classifier", "method": "classify"},
            {"service": "document_extractor", "method": "extract"},
            {"service": "notification", "method": "send"},
        ]
        estimate = await quality_svc.estimate_pipeline_cost(steps)
        assert isinstance(estimate, CostEstimate)
        assert estimate.estimated_tokens > 0
        assert estimate.estimated_cost_usd > 0.0
        assert estimate.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_estimate_cost_custom_model(
        self, quality_svc: QualityService
    ) -> None:
        """Cost estimation with a different model."""
        await quality_svc.start()
        steps = [{"service": "classifier", "method": "classify"}]
        estimate = await quality_svc.estimate_pipeline_cost(
            steps, model="gpt-4o"
        )
        assert estimate.model == "gpt-4o"
        assert estimate.estimated_cost_usd > 0.0

    @pytest.mark.asyncio
    async def test_estimate_cost_empty_steps(
        self, quality_svc: QualityService
    ) -> None:
        """Empty step list returns zero cost."""
        await quality_svc.start()
        estimate = await quality_svc.estimate_pipeline_cost([])
        assert estimate.estimated_tokens == 0
        assert estimate.estimated_cost_usd == 0.0


# ===========================================================================
# TestAdapterRegistration
# ===========================================================================


class TestQualityAdapterRegistration:
    def test_quality_adapter_registered(self) -> None:
        """Quality adapter is registered in the adapter registry."""
        import aiflow.pipeline.adapters.quality_adapter  # noqa: F401
        from aiflow.pipeline.adapter_base import adapter_registry

        assert adapter_registry.has("quality", "evaluate_rubric"), (
            "Adapter (quality, evaluate_rubric) not found in registry. "
            f"Available: {adapter_registry.list_adapters()}"
        )

    def test_adapter_schemas(self) -> None:
        """Quality adapter has Pydantic input/output schemas."""
        from pydantic import BaseModel as PydanticBaseModel

        import aiflow.pipeline.adapters.quality_adapter  # noqa: F401
        from aiflow.pipeline.adapter_base import adapter_registry

        adapter = adapter_registry.get("quality", "evaluate_rubric")
        assert issubclass(adapter.input_schema, PydanticBaseModel)
        assert issubclass(adapter.output_schema, PydanticBaseModel)

    def test_adapter_service_method_names(self) -> None:
        """Adapter service_name and method_name match expected values."""
        import aiflow.pipeline.adapters.quality_adapter  # noqa: F401
        from aiflow.pipeline.adapter_base import adapter_registry

        adapter = adapter_registry.get("quality", "evaluate_rubric")
        assert adapter.service_name == "quality"
        assert adapter.method_name == "evaluate_rubric"
