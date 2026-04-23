"""Async CRUD + read projection for ``tenant_budgets`` (Alembic 045).

Scope for S121 — persistence, upsert, delete, and one live read helper
``get_remaining`` that projects :class:`BudgetView` from the running cost
over the matching period window. Pre-flight refusal and LLM-call gating
land in S122 and consume this service; nothing here raises on over-budget.
"""

from __future__ import annotations

import asyncpg
import structlog

from aiflow.services.tenant_budgets.contracts import (
    PERIOD_WINDOW_H,
    BudgetPeriod,
    BudgetView,
    TenantBudget,
)
from aiflow.state.cost_repository import CostAttributionRepository

__all__ = ["TenantBudgetService"]

logger = structlog.get_logger(__name__)


_SELECT_COLUMNS = (
    "id, tenant_id, period, limit_usd, alert_threshold_pct, enabled, created_at, updated_at"
)


def _row_to_budget(row: asyncpg.Record) -> TenantBudget:
    return TenantBudget(
        id=row["id"],
        tenant_id=row["tenant_id"],
        period=row["period"],
        limit_usd=float(row["limit_usd"]),
        alert_threshold_pct=list(row["alert_threshold_pct"] or []),
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class TenantBudgetService:
    """Persistence + read projection for per-tenant spending budgets."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        cost_repo: CostAttributionRepository | None = None,
    ) -> None:
        self._pool = pool
        self._cost_repo = cost_repo or CostAttributionRepository(pool)

    async def get(
        self,
        tenant_id: str,
        period: BudgetPeriod,
    ) -> TenantBudget | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_SELECT_COLUMNS} FROM tenant_budgets "
                "WHERE tenant_id = $1 AND period = $2",
                tenant_id,
                period,
            )
        return _row_to_budget(row) if row else None

    async def list(self, tenant_id: str) -> list[TenantBudget]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_SELECT_COLUMNS} FROM tenant_budgets "
                "WHERE tenant_id = $1 ORDER BY period",
                tenant_id,
            )
        return [_row_to_budget(r) for r in rows]

    async def upsert(self, budget: TenantBudget) -> TenantBudget:
        # Re-validate thresholds via the Pydantic validator (sort + range).
        normalized = TenantBudget.model_validate(budget.model_dump())
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO tenant_budgets (
                    tenant_id, period, limit_usd,
                    alert_threshold_pct, enabled, updated_at
                )
                VALUES ($1, $2, $3, $4::integer[], $5, NOW())
                ON CONFLICT (tenant_id, period) DO UPDATE SET
                    limit_usd = EXCLUDED.limit_usd,
                    alert_threshold_pct = EXCLUDED.alert_threshold_pct,
                    enabled = EXCLUDED.enabled,
                    updated_at = NOW()
                RETURNING {_SELECT_COLUMNS}
                """,
                normalized.tenant_id,
                normalized.period,
                normalized.limit_usd,
                normalized.alert_threshold_pct,
                normalized.enabled,
            )
        logger.info(
            "tenant_budget_upserted",
            tenant_id=normalized.tenant_id,
            period=normalized.period,
            limit_usd=normalized.limit_usd,
        )
        return _row_to_budget(row)

    async def delete(self, tenant_id: str, period: BudgetPeriod) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tenant_budgets WHERE tenant_id = $1 AND period = $2",
                tenant_id,
                period,
            )
        # asyncpg status is 'DELETE <n>'.
        deleted = not result.endswith(" 0")
        if deleted:
            logger.info("tenant_budget_deleted", tenant_id=tenant_id, period=period)
        return deleted

    async def get_remaining(
        self,
        tenant_id: str,
        period: BudgetPeriod,
    ) -> BudgetView | None:
        budget = await self.get(tenant_id, period)
        if budget is None:
            return None
        window_h = PERIOD_WINDOW_H[period]
        used = await self._cost_repo.aggregate_running_cost(tenant_id, window_h)
        return BudgetView.from_budget(budget, used_usd=used)
