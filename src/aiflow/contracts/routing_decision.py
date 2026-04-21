"""RoutingDecision — v1 stub emitted by MultiSignalRouter.

Records which parser was chosen for a file plus the rule signals that
drove the decision. Downstream stages read ``chosen_parser`` to pick a
provider instance and ``fallback_chain`` on parse failure.

Full v2 shape (per-field cost breakdown, scan-aware signals, HITL hints)
arrives in Phase 2b (v1.5.1). Scan-aware routing is S96 scope; here the
signal set is deliberately narrow — ``size_bytes``, ``mime_type``,
``cloud_ai_allowed``, optional ``page_count``.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md §7 (RoutingDecision),
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I / §10.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "RoutingDecision",
]


class RoutingDecision(BaseModel):
    """Router output for a single file within an IntakePackage."""

    model_config = ConfigDict(extra="forbid")

    package_id: UUID = Field(..., description="Owning IntakePackage.package_id.")
    file_id: UUID = Field(..., description="IntakeFile.file_id this decision covers.")
    tenant_id: str = Field(..., min_length=1, description="Tenant boundary.")

    chosen_parser: str = Field(
        ...,
        min_length=1,
        description=(
            "Parser provider identifier (e.g. 'unstructured_fast', "
            "'docling_standard') or the sentinel 'skipped_policy' when a "
            "policy gate blocked extraction."
        ),
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Human-readable rule magyarázat a kiválasztáshoz.",
    )
    signals: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Input signals that drove the rule (size_bytes, mime_type, "
            "cloud_ai_allowed, page_count...)."
        ),
    )
    fallback_chain: list[str] = Field(
        default_factory=list,
        description="Ordered fallback parser names to try on primary failure.",
    )
    cost_estimate: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated processing cost for the chosen parser.",
    )
    decided_at: datetime = Field(default_factory=datetime.utcnow)
