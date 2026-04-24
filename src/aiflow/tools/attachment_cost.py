"""Per-attachment cost estimation — Sprint O FU-7.

Maps a processed attachment's ``processor_used`` + page count onto a USD
cost estimate. Docling is local/free (0.0). Azure Document Intelligence
charges per page (prebuilt-layout → ~$0.01/page as of 2026-04; prebuilt-
document → higher). LLM vision is approximated from the token budget
docling + a frontier model would burn on one image.

Used by the email-connector orchestrator (Sprint O / S127 helper) to
emit a ``cost_records`` row per attachment so per-tenant budgets see
attachment processing alongside LLM classification cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiflow.tools.attachment_processor import ProcessedAttachment

__all__ = [
    "AttachmentCostEstimator",
    "estimate_attachment_cost",
    "DOCLING_COST_PER_PAGE_USD",
    "AZURE_DI_LAYOUT_COST_PER_PAGE_USD",
    "AZURE_DI_DOCUMENT_COST_PER_PAGE_USD",
    "LLM_VISION_COST_PER_IMAGE_USD",
]

# Pricing table — intentionally explicit so a cost review can diff this
# single file against Azure / OpenAI published pricing.
DOCLING_COST_PER_PAGE_USD = 0.0
AZURE_DI_LAYOUT_COST_PER_PAGE_USD = 0.010  # prebuilt-layout, pay-as-you-go
AZURE_DI_DOCUMENT_COST_PER_PAGE_USD = 0.050  # prebuilt-document / custom
LLM_VISION_COST_PER_IMAGE_USD = 0.004  # ~4k tokens @ gpt-4o-mini image rate


class AttachmentCostEstimator:
    """Pure-function helper — maps processor + page count → USD."""

    def __init__(
        self,
        *,
        docling_cost_per_page: float = DOCLING_COST_PER_PAGE_USD,
        azure_di_cost_per_page: float = AZURE_DI_LAYOUT_COST_PER_PAGE_USD,
        llm_vision_cost_per_image: float = LLM_VISION_COST_PER_IMAGE_USD,
    ) -> None:
        self._docling_per_page = docling_cost_per_page
        self._azure_di_per_page = azure_di_cost_per_page
        self._llm_vision_per_image = llm_vision_cost_per_image

    def estimate(self, processed: ProcessedAttachment) -> tuple[float, int]:
        """Return ``(cost_usd, pages_processed)`` for a processed attachment.

        Returns ``(0.0, 0)`` for failed attachments (``error != ""``) so they
        don't leak into the tenant budget.
        """
        if processed.error:
            return 0.0, 0

        pages = int(processed.metadata.get("pages") or processed.metadata.get("page_count") or 1)
        pages = max(1, pages)

        processor = (processed.processor_used or "").lower()
        if processor == "docling":
            cost = self._docling_per_page * pages
        elif processor.startswith("azure"):
            cost = self._azure_di_per_page * pages
        elif "llm_vision" in processor or "vision" in processor:
            cost = self._llm_vision_per_image  # flat per image
        else:
            # Unknown / placeholder / failed processors: treat as free so
            # we never over-charge a tenant on a processor we didn't price.
            cost = 0.0

        return round(cost, 6), pages


def estimate_attachment_cost(processed: ProcessedAttachment) -> tuple[float, int]:
    """Module-level shortcut for the default estimator."""
    return AttachmentCostEstimator().estimate(processed)
