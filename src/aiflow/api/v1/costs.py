"""Cost tracking and aggregation endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from aiflow.api.deps import get_pool

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/costs", tags=["costs"])


class SkillCost(BaseModel):
    """Cost summary for a single skill."""
    skill_name: str
    total_cost_usd: float
    run_count: int
    avg_cost_usd: float


class DailyCost(BaseModel):
    """Cost for a single day."""
    date: str
    total_cost_usd: float
    run_count: int


class CostsSummaryResponse(BaseModel):
    """Aggregated cost summary."""
    total_cost_usd: float = 0.0
    total_runs: int = 0
    per_skill: list[SkillCost] = []
    daily: list[DailyCost] = []


@router.get("/summary", response_model=CostsSummaryResponse)
async def costs_summary() -> CostsSummaryResponse:
    """Get aggregated cost summary by skill and by day."""
    result = CostsSummaryResponse()

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Per-skill aggregation
            skill_rows = await conn.fetch(
                """
                SELECT
                    COALESCE(skill_name, workflow_name) AS skill,
                    COALESCE(SUM(total_cost_usd), 0) AS total_cost,
                    COUNT(*) AS run_count
                FROM workflow_runs
                GROUP BY COALESCE(skill_name, workflow_name)
                ORDER BY total_cost DESC
                """
            )
            for row in skill_rows:
                rc = row["run_count"]
                tc = float(row["total_cost"] or 0)
                result.per_skill.append(SkillCost(
                    skill_name=row["skill"],
                    total_cost_usd=tc,
                    run_count=rc,
                    avg_cost_usd=tc / rc if rc > 0 else 0,
                ))
                result.total_cost_usd += tc
                result.total_runs += rc

            # Daily aggregation (last 30 days)
            daily_rows = await conn.fetch(
                """
                SELECT
                    DATE(started_at) AS day,
                    COALESCE(SUM(total_cost_usd), 0) AS total_cost,
                    COUNT(*) AS run_count
                FROM workflow_runs
                WHERE started_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(started_at)
                ORDER BY day DESC
                """
            )
            for row in daily_rows:
                result.daily.append(DailyCost(
                    date=row["day"].isoformat() if row["day"] else "",
                    total_cost_usd=float(row["total_cost"] or 0),
                    run_count=row["run_count"],
                ))
    except Exception as e:
        logger.warning("costs_db_failed", error=str(e))

    return result
