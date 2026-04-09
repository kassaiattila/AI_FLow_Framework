"""
@test_registry:
    suite: service-unit
    component: services.classifier
    covers: [src/aiflow/services/classifier/service.py]
    phase: B2.1
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, classifier, keywords, llm]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.classifier.service import (
    ClassificationResult,
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
)

SCHEMA_LABELS = [
    {
        "id": "complaint",
        "display_name": "Complaint",
        "description": "Customer complaint",
        "keywords": ["complaint", "unhappy", "dissatisfied", "problem", "issue"],
    },
    {
        "id": "inquiry",
        "display_name": "Inquiry",
        "description": "General inquiry",
        "keywords": ["question", "info", "information", "how", "when"],
    },
    {
        "id": "order",
        "display_name": "Order",
        "description": "Order-related",
        "keywords": ["order", "purchase", "buy", "delivery"],
    },
]


@pytest.fixture()
def svc() -> ClassifierService:
    """Classifier with sklearn_only strategy and no LLM."""
    config = ClassifierConfig(
        strategy=ClassificationStrategy.SKLEARN_ONLY,
        confidence_threshold=0.5,
    )
    return ClassifierService(config=config)


class TestClassifierService:
    @pytest.mark.asyncio
    async def test_classify_keywords_strategy(self, svc: ClassifierService) -> None:
        """Keywords strategy returns correct label based on keyword hits."""
        result = await svc.classify(
            text="I have a complaint about my order, I am very unhappy",
            schema_labels=SCHEMA_LABELS,
        )
        assert isinstance(result, ClassificationResult)
        assert result.label == "complaint"
        assert result.confidence > 0
        assert result.method == "keywords"

    @pytest.mark.asyncio
    async def test_classify_confidence_above_threshold(self, svc: ClassifierService) -> None:
        """When keyword confidence is above threshold, result is accepted."""
        result = await svc.classify(
            text="I am unhappy and dissatisfied, this complaint is a real problem and an issue",
            schema_labels=SCHEMA_LABELS,
        )
        assert result.confidence >= svc.confidence_threshold
        assert result.label == "complaint"

    @pytest.mark.asyncio
    async def test_classify_confidence_below_threshold(self) -> None:
        """When keyword confidence is low and no LLM, returns keywords_only_no_llm."""
        config = ClassifierConfig(
            strategy=ClassificationStrategy.SKLEARN_FIRST,
            confidence_threshold=0.99,
        )
        svc = ClassifierService(config=config, models_client=None)
        result = await svc.classify(text="hello", schema_labels=SCHEMA_LABELS)
        assert result.method == "keywords_only_no_llm"

    @pytest.mark.asyncio
    async def test_classify_ensemble(self) -> None:
        """Ensemble strategy merges keyword and LLM results."""
        mock_client = MagicMock()
        mock_output = MagicMock()
        mock_output.text = '{"label": "complaint", "confidence": 0.9, "reasoning": "test"}'
        mock_result = MagicMock()
        mock_result.output = mock_output
        mock_client.generate = AsyncMock(return_value=mock_result)

        config = ClassifierConfig(
            strategy=ClassificationStrategy.ENSEMBLE,
            confidence_threshold=0.5,
        )
        svc = ClassifierService(config=config, models_client=mock_client)
        result = await svc.classify(
            text="I have a complaint, very unhappy",
            schema_labels=SCHEMA_LABELS,
        )
        assert result.label == "complaint"
        assert "ensemble" in result.method or "hybrid" in result.method

    @pytest.mark.asyncio
    async def test_health_check(self, svc: ClassifierService) -> None:
        """health_check returns True for in-memory classifier."""
        assert await svc.health_check() is True
