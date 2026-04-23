"""Pydantic contracts for the per-tenant budget service.

* :class:`TenantBudget` — persisted row in ``tenant_budgets`` (Alembic 045).
* :class:`BudgetView` — live read-side projection returned by
  :meth:`TenantBudgetService.get_remaining`: limit minus running cost over
  the period window, plus the crossed alert thresholds so the pre-flight
  guardrail (S122) and the admin UI (S123) share one payload.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "BUDGET_PERIOD_DAILY",
    "BUDGET_PERIOD_MONTHLY",
    "BudgetPeriod",
    "BudgetView",
    "TenantBudget",
]

BUDGET_PERIOD_DAILY = "daily"
BUDGET_PERIOD_MONTHLY = "monthly"

BudgetPeriod = Literal["daily", "monthly"]

# ``period`` → window length fed to
# ``CostAttributionRepository.aggregate_running_cost``. Monthly uses a
# calendar-month approximation (30 * 24h); S122 may refine if the benchmark
# shows drift.
PERIOD_WINDOW_H: dict[str, int] = {
    BUDGET_PERIOD_DAILY: 24,
    BUDGET_PERIOD_MONTHLY: 24 * 30,
}


class TenantBudget(BaseModel):
    """A persisted per-tenant budget row."""

    id: UUID | None = None
    tenant_id: str = Field(..., min_length=1, max_length=255)
    period: BudgetPeriod
    limit_usd: float = Field(..., ge=0.0)
    alert_threshold_pct: list[int] = Field(default_factory=lambda: [50, 80, 95])
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("alert_threshold_pct")
    @classmethod
    def _validate_thresholds(cls, value: list[int]) -> list[int]:
        if not value:
            return []
        for pct in value:
            if pct < 1 or pct > 100:
                raise ValueError(f"alert_threshold_pct values must be in [1, 100] (got {pct})")
        deduped = sorted(set(value))
        return deduped


class BudgetView(BaseModel):
    """Live projection of a budget row against the tenant's running cost."""

    tenant_id: str
    period: BudgetPeriod
    limit_usd: float
    used_usd: float
    remaining_usd: float
    usage_pct: float
    alert_threshold_pct: list[int]
    over_thresholds: list[int]
    enabled: bool
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_budget(cls, budget: TenantBudget, used_usd: float) -> BudgetView:
        limit = max(budget.limit_usd, 0.0)
        used = max(used_usd, 0.0)
        remaining = round(limit - used, 6)
        usage_pct = round((used / limit) * 100.0, 4) if limit > 0 else 0.0
        over = [t for t in budget.alert_threshold_pct if usage_pct >= t] if limit > 0 else []
        return cls(
            tenant_id=budget.tenant_id,
            period=budget.period,
            limit_usd=limit,
            used_usd=used,
            remaining_usd=remaining,
            usage_pct=usage_pct,
            alert_threshold_pct=list(budget.alert_threshold_pct),
            over_thresholds=over,
            enabled=budget.enabled,
        )
