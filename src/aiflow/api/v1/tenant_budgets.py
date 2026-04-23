"""Per-tenant budget CRUD endpoints — Sprint N / S121.

GET / PUT / DELETE backed by
:class:`aiflow.services.tenant_budgets.TenantBudgetService`. Auth gating is
inherited from the global ``AuthMiddleware`` (same pattern as
``/api/v1/costs/*``). The admin UI dashboard (S123) and the pre-flight
guardrail (S122) both consume :class:`BudgetView`.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field, field_validator

from aiflow.api.deps import get_pool
from aiflow.services.tenant_budgets import (
    BudgetPeriod,
    BudgetView,
    TenantBudget,
    TenantBudgetService,
)

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/tenants", tags=["tenant-budgets"])


TenantIdPath = Annotated[str, Path(min_length=1, max_length=255)]
PeriodPath = Annotated[BudgetPeriod, Path()]


class TenantBudgetUpsertRequest(BaseModel):
    """PUT body — immutable fields (tenant_id, period) come from the path."""

    limit_usd: float = Field(..., ge=0.0)
    alert_threshold_pct: list[int] = Field(default_factory=lambda: [50, 80, 95])
    enabled: bool = True

    @field_validator("alert_threshold_pct")
    @classmethod
    def _validate_thresholds(cls, value: list[int]) -> list[int]:
        for pct in value:
            if pct < 1 or pct > 100:
                raise ValueError(f"alert_threshold_pct values must be in [1, 100] (got {pct})")
        return sorted(set(value))


class TenantBudgetGetResponse(BaseModel):
    """GET response — persisted row plus the live projection."""

    budget: TenantBudget
    view: BudgetView


async def _service() -> TenantBudgetService:
    pool = await get_pool()
    return TenantBudgetService(pool)


@router.get("/{tenant_id}/budget", response_model=list[TenantBudgetGetResponse])
async def list_tenant_budgets(
    tenant_id: TenantIdPath,
) -> list[TenantBudgetGetResponse]:
    """All budget rows for a tenant, each paired with the live :class:`BudgetView`."""
    svc = await _service()
    budgets = await svc.list(tenant_id)
    out: list[TenantBudgetGetResponse] = []
    for budget in budgets:
        view = await svc.get_remaining(tenant_id, budget.period)
        # ``view`` is not None here — get_remaining only returns None on missing row.
        assert view is not None
        out.append(TenantBudgetGetResponse(budget=budget, view=view))
    return out


@router.get(
    "/{tenant_id}/budget/{period}",
    response_model=TenantBudgetGetResponse,
)
async def get_tenant_budget(
    tenant_id: TenantIdPath,
    period: PeriodPath,
) -> TenantBudgetGetResponse:
    svc = await _service()
    budget = await svc.get(tenant_id, period)
    if budget is None:
        raise HTTPException(status_code=404, detail="tenant_budget_not_found")
    view = await svc.get_remaining(tenant_id, period)
    assert view is not None
    return TenantBudgetGetResponse(budget=budget, view=view)


@router.put(
    "/{tenant_id}/budget/{period}",
    response_model=TenantBudgetGetResponse,
)
async def upsert_tenant_budget(
    tenant_id: TenantIdPath,
    period: PeriodPath,
    payload: TenantBudgetUpsertRequest,
) -> TenantBudgetGetResponse:
    svc = await _service()
    budget = TenantBudget(
        tenant_id=tenant_id,
        period=period,
        limit_usd=payload.limit_usd,
        alert_threshold_pct=payload.alert_threshold_pct,
        enabled=payload.enabled,
    )
    stored = await svc.upsert(budget)
    view = await svc.get_remaining(tenant_id, period)
    assert view is not None
    return TenantBudgetGetResponse(budget=stored, view=view)


@router.delete("/{tenant_id}/budget/{period}")
async def delete_tenant_budget(
    tenant_id: TenantIdPath,
    period: PeriodPath,
) -> dict[str, bool]:
    svc = await _service()
    deleted = await svc.delete(tenant_id, period)
    if not deleted:
        raise HTTPException(status_code=404, detail="tenant_budget_not_found")
    return {"deleted": True}
