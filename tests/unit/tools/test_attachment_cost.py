"""
@test_registry:
    suite: tools-unit
    component: tools.attachment_cost (FU-7 estimator)
    covers: [src/aiflow/tools/attachment_cost.py]
    phase: sprint-o-fu-7
    priority: high
    estimated_duration_ms: 120
    requires_services: []
    tags: [tools, attachment, cost, sprint-o, fu-7]

Sprint O FU-7 — pure-function pricing table coverage + the
``AttachmentCostEstimator.estimate`` dispatch matrix.
"""

from __future__ import annotations

from aiflow.tools.attachment_cost import (
    AZURE_DI_LAYOUT_COST_PER_PAGE_USD,
    DOCLING_COST_PER_PAGE_USD,
    LLM_VISION_COST_PER_IMAGE_USD,
    AttachmentCostEstimator,
    estimate_attachment_cost,
)
from aiflow.tools.attachment_processor import ProcessedAttachment


def _att(processor: str, *, pages: int = 1, error: str = "") -> ProcessedAttachment:
    return ProcessedAttachment(
        filename=f"{processor}.pdf",
        mime_type="application/pdf",
        processor_used=processor,
        metadata={"pages": pages},
        error=error,
    )


class TestPricingConstants:
    def test_docling_is_free(self) -> None:
        assert DOCLING_COST_PER_PAGE_USD == 0.0

    def test_azure_di_layout_is_positive(self) -> None:
        assert AZURE_DI_LAYOUT_COST_PER_PAGE_USD > 0.0

    def test_llm_vision_is_positive(self) -> None:
        assert LLM_VISION_COST_PER_IMAGE_USD > 0.0


class TestEstimatorDispatch:
    def test_docling_free(self) -> None:
        est = AttachmentCostEstimator()
        cost, pages = est.estimate(_att("docling", pages=5))
        assert cost == 0.0
        assert pages == 5

    def test_azure_di_scaled_per_page(self) -> None:
        est = AttachmentCostEstimator()
        cost, pages = est.estimate(_att("azure_di", pages=10))
        assert pages == 10
        assert cost == round(AZURE_DI_LAYOUT_COST_PER_PAGE_USD * 10, 6)

    def test_azure_variant_name_also_matches(self) -> None:
        # processor_used="azure_failed" or "azure_di_failed" should still
        # map to the Azure tier for cost attribution.
        est = AttachmentCostEstimator()
        cost, _ = est.estimate(_att("azure_di_layout", pages=3))
        assert cost == round(AZURE_DI_LAYOUT_COST_PER_PAGE_USD * 3, 6)

    def test_llm_vision_flat_per_image(self) -> None:
        est = AttachmentCostEstimator()
        cost, pages = est.estimate(_att("llm_vision", pages=7))
        # LLM vision charges per image, not per page.
        assert pages == 7
        assert cost == LLM_VISION_COST_PER_IMAGE_USD

    def test_unknown_processor_is_free(self) -> None:
        est = AttachmentCostEstimator()
        cost, _ = est.estimate(_att("custom_stub", pages=2))
        assert cost == 0.0

    def test_failed_attachment_is_free(self) -> None:
        est = AttachmentCostEstimator()
        cost, pages = est.estimate(_att("azure_di", pages=10, error="timeout"))
        assert cost == 0.0
        assert pages == 0

    def test_missing_pages_defaults_to_one(self) -> None:
        est = AttachmentCostEstimator()
        att = ProcessedAttachment(
            filename="x.pdf",
            processor_used="azure_di",
            metadata={},
        )
        cost, pages = est.estimate(att)
        assert pages == 1
        assert cost == AZURE_DI_LAYOUT_COST_PER_PAGE_USD

    def test_module_level_shortcut_matches_default_estimator(self) -> None:
        att = _att("docling", pages=3)
        assert estimate_attachment_cost(att) == AttachmentCostEstimator().estimate(att)


class TestCustomPricing:
    def test_override_per_page(self) -> None:
        est = AttachmentCostEstimator(
            docling_cost_per_page=0.0,
            azure_di_cost_per_page=0.02,
            llm_vision_cost_per_image=0.01,
        )
        assert est.estimate(_att("azure_di", pages=5))[0] == 0.1
        assert est.estimate(_att("llm_vision"))[0] == 0.01
