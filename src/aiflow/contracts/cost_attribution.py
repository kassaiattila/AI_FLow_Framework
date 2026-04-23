"""CostAttribution — per-call cost ledger entry attributed to a tenant.

Source: 01_PLAN/110_USE_CASE_FIRST_REPLAN.md §4 Sprint L (S112).

Emitted whenever a tenant-scoped provider call (extractor / embedder / llm)
produces a measurable cost. Rows are persisted to the `cost_records` table
(Alembic 006 + 043 tenant_id extension) and aggregated by
``PolicyEngine.enforce_cost_cap`` to decide whether further work is allowed
in the current window.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

__all__ = ["CostAttribution"]


class CostAttribution(BaseModel):
    """A single cost ledger entry attributed to a tenant."""

    tenant_id: str = Field(..., min_length=1, max_length=255)
    run_id: str | None = None
    skill: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=255)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
