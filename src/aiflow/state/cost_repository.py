"""Cost ledger repository — tenant-scoped reads/writes over `cost_records`.

Source: 01_PLAN/110_USE_CASE_FIRST_REPLAN.md §4 Sprint L (S112).

Wraps ``cost_records`` (Alembic 006 + 043 tenant_id) behind a small async
API so ``PolicyEngine.enforce_cost_cap`` and the ``/api/v1/costs/cap-status``
endpoint share the same aggregation query.
"""

from __future__ import annotations

import uuid

import asyncpg
import structlog

from aiflow.contracts.cost_attribution import CostAttribution

__all__ = ["CostAttributionRepository"]

logger = structlog.get_logger(__name__)


class CostAttributionRepository:
    """Async repository backed by asyncpg for cost ledger operations."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert_attribution(self, attribution: CostAttribution) -> None:
        """Insert a new cost attribution row. Best-effort logging on failure."""
        run_uuid: uuid.UUID | None = None
        if attribution.run_id:
            try:
                run_uuid = uuid.UUID(attribution.run_id)
            except (ValueError, AttributeError):
                run_uuid = None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cost_records
                    (id, workflow_run_id, step_name, model, provider,
                     input_tokens, output_tokens, cost_usd, tenant_id, recorded_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                uuid.uuid4(),
                run_uuid,
                attribution.skill,
                attribution.model,
                attribution.provider,
                attribution.input_tokens,
                attribution.output_tokens,
                attribution.cost_usd,
                attribution.tenant_id,
                attribution.recorded_at,
            )
        logger.debug(
            "cost_attribution_inserted",
            tenant_id=attribution.tenant_id,
            provider=attribution.provider,
            cost_usd=round(attribution.cost_usd, 6),
        )

    async def aggregate_running_cost(self, tenant_id: str, window_h: int) -> float:
        """Return the sum of cost_usd for a tenant over the last ``window_h`` hours."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(cost_usd), 0) AS total
                FROM cost_records
                WHERE tenant_id = $1
                  AND recorded_at >= NOW() - ($2 || ' hours')::interval
                """,
                tenant_id,
                str(window_h),
            )
        total = float(row["total"] or 0) if row else 0.0
        return total
