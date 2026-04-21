"""ExtractionResult — v1 stub returned by DocumentExtractorService.extract_from_package().

v2 upgrade (full §10.3 shape with per-field provenance, confidence scores
per field, and structured cost attribution) is Phase 2b (v1.5.1) scope.

Distinct from the legacy ``aiflow.services.document_extractor.service.ExtractionResult``
which pins the v1.3 → v1.4 backward-compat shim output. The two models are
intentionally separate: the legacy one is a stability anchor for the
extract(file_path) callers; this one is the forward-looking contract for
the IntakePackage-based API.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md §10,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ExtractionResult",
]


class ExtractionResult(BaseModel):
    """Extraction output for a single file within an IntakePackage."""

    model_config = ConfigDict(extra="forbid")

    package_id: UUID = Field(..., description="Owning IntakePackage.package_id.")
    file_id: UUID = Field(..., description="IntakeFile.file_id this result corresponds to.")
    tenant_id: str = Field(..., min_length=1, description="Tenant boundary.")

    parser_used: str = Field(
        ...,
        min_length=1,
        description=(
            "Parser provider identifier (e.g. 'docling_standard') or a sentinel "
            "like 'skipped_policy' when a policy gate blocked extraction."
        ),
    )
    extracted_text: str = Field(
        default="",
        description="Parsed plain-text content. Empty when the file was skipped.",
    )
    structured_fields: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured fields keyed by field name. In S94 this is populated by "
            "the parser's tables/metadata only; LLM field extraction arrives in S95."
        ),
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall extraction confidence (0..1).",
    )

    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    cost_attribution: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Per-provider cost breakdown (parser_cost, extractor_cost, ...). "
            "Filled by the cost_tracker; None when costs are not tracked."
        ),
    )
