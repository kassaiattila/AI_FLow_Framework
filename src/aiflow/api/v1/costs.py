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


class TeamDailyCost(BaseModel):
    """Daily cost per team from v_daily_team_costs view."""
    team_name: str | None = None
    cost_date: str
    model: str | None = None
    request_count: int = 0
    total_cost_usd: float = 0.0


class BudgetStatus(BaseModel):
    """Team budget status from v_monthly_budget view."""
    team_name: str | None = None
    budget_limit_usd: float = 0.0
    used_usd: float = 0.0
    remaining_usd: float = 0.0
    usage_pct: float = 0.0
    alert_level: str = "ok"


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


@router.get("/team-daily", response_model=list[TeamDailyCost])
async def team_daily_costs() -> list[TeamDailyCost]:
    """Get daily costs per team (uses v_daily_team_costs view)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT team_name, cost_date, model, request_count, total_cost_usd "
                "FROM v_daily_team_costs ORDER BY cost_date DESC LIMIT 100"
            )
            return [
                TeamDailyCost(
                    team_name=r["team_name"],
                    cost_date=r["cost_date"].isoformat() if r["cost_date"] else "",
                    model=r["model"],
                    request_count=r["request_count"] or 0,
                    total_cost_usd=float(r["total_cost_usd"] or 0),
                )
                for r in rows
            ]
    except Exception as e:
        logger.warning("team_daily_costs_failed", error=str(e))
        return []


@router.get("/budget", response_model=list[BudgetStatus])
async def budget_status() -> list[BudgetStatus]:
    """Get monthly budget status per team (uses v_monthly_budget view)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT team_name, budget_limit_usd, used_usd, remaining_usd, usage_pct, alert_level "
                "FROM v_monthly_budget ORDER BY usage_pct DESC"
            )
            return [
                BudgetStatus(
                    team_name=r["team_name"],
                    budget_limit_usd=float(r["budget_limit_usd"] or 0),
                    used_usd=float(r["used_usd"] or 0),
                    remaining_usd=float(r["remaining_usd"] or 0),
                    usage_pct=float(r["usage_pct"] or 0),
                    alert_level=r["alert_level"] or "ok",
                )
                for r in rows
            ]
    except Exception as e:
        logger.warning("budget_status_failed", error=str(e))
        return []


class ModelCostItem(BaseModel):
    """Cost breakdown per model."""
    model: str
    provider: str
    request_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0


class CostRecordsBreakdown(BaseModel):
    """Detailed cost breakdown from cost_records table."""
    per_model: list[ModelCostItem] = []
    total_records: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    source: str = "backend"


@router.get("/breakdown", response_model=CostRecordsBreakdown)
async def cost_breakdown() -> CostRecordsBreakdown:
    """Get detailed cost breakdown by model from cost_records table."""
    result = CostRecordsBreakdown()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    model,
                    provider,
                    COUNT(*) AS request_count,
                    COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                    COALESCE(SUM(cost_usd), 0) AS total_cost_usd
                FROM cost_records
                GROUP BY model, provider
                ORDER BY total_cost_usd DESC
                """
            )
            for r in rows:
                inp = int(r["total_input_tokens"])
                out = int(r["total_output_tokens"])
                cost = float(r["total_cost_usd"])
                result.per_model.append(ModelCostItem(
                    model=r["model"],
                    provider=r["provider"],
                    request_count=r["request_count"],
                    total_input_tokens=inp,
                    total_output_tokens=out,
                    total_cost_usd=cost,
                ))
                result.total_records += r["request_count"]
                result.total_tokens += inp + out
                result.total_cost_usd += cost
    except Exception as e:
        logger.warning("cost_breakdown_failed", error=str(e))
    return result
