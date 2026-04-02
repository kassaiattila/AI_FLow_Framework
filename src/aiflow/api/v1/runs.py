"""Workflow run listing and detail endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aiflow.api.deps import get_pool

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class StepRunItem(BaseModel):
    """A single step execution within a workflow run."""
    step_name: str
    status: str
    duration_ms: float | None = None
    cost_usd: float = 0.0
    model_used: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None


class RunItem(BaseModel):
    """A workflow run summary."""
    run_id: str
    workflow_name: str
    skill_name: str | None = None
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    total_duration_ms: float | None = None
    total_cost_usd: float = 0.0
    steps: list[StepRunItem] = []


class RunListResponse(BaseModel):
    """Paginated list of workflow runs."""
    runs: list[RunItem]
    total: int


@router.get("", response_model=RunListResponse)
async def list_runs(
    skill: str | None = Query(None, description="Filter by skill name"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> RunListResponse:
    """List workflow runs with optional filtering."""
    runs: list[RunItem] = []
    total = 0

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Build query with optional filters
            where_clauses: list[str] = []
            params: list[Any] = []
            idx = 1

            if skill:
                where_clauses.append(f"r.skill_name = ${idx}")
                params.append(skill)
                idx += 1
            if status:
                where_clauses.append(f"r.status = ${idx}")
                params.append(status)
                idx += 1

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Count
            count_row = await conn.fetchrow(
                f"SELECT COUNT(*) AS cnt FROM workflow_runs r {where_sql}",
                *params,
            )
            total = count_row["cnt"] if count_row else 0

            # Fetch runs
            params.extend([limit, offset])
            rows = await conn.fetch(
                f"""
                SELECT r.id, r.workflow_name, r.skill_name, r.status,
                       r.started_at, r.completed_at, r.total_duration_ms, r.total_cost_usd
                FROM workflow_runs r
                {where_sql}
                ORDER BY r.started_at DESC NULLS LAST
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params,
            )

            run_ids = [row["id"] for row in rows]

            # Fetch steps for all runs in one query
            steps_by_run: dict[str, list[StepRunItem]] = {}
            if run_ids:
                step_rows = await conn.fetch(
                    """
                    SELECT workflow_run_id, step_name, status, duration_ms,
                           cost_usd, model_used, input_tokens, output_tokens, error
                    FROM step_runs
                    WHERE workflow_run_id = ANY($1::uuid[])
                    ORDER BY step_index
                    """,
                    run_ids,
                )
                for sr in step_rows:
                    rid = str(sr["workflow_run_id"])
                    if rid not in steps_by_run:
                        steps_by_run[rid] = []
                    steps_by_run[rid].append(StepRunItem(
                        step_name=sr["step_name"],
                        status=sr["status"],
                        duration_ms=sr["duration_ms"],
                        cost_usd=sr["cost_usd"] or 0.0,
                        model_used=sr["model_used"],
                        input_tokens=sr["input_tokens"],
                        output_tokens=sr["output_tokens"],
                        error=sr["error"],
                    ))

            for row in rows:
                rid = str(row["id"])
                runs.append(RunItem(
                    run_id=rid,
                    workflow_name=row["workflow_name"],
                    skill_name=row["skill_name"],
                    status=row["status"],
                    started_at=row["started_at"].isoformat() if row["started_at"] else None,
                    completed_at=row["completed_at"].isoformat() if row["completed_at"] else None,
                    total_duration_ms=row["total_duration_ms"],
                    total_cost_usd=row["total_cost_usd"] or 0.0,
                    steps=steps_by_run.get(rid, []),
                ))
    except Exception as e:
        logger.warning("runs_db_failed", error=str(e))


    return RunListResponse(runs=runs, total=total)


class DailyStats(BaseModel):
    """Stats for a single day."""
    date: str
    run_count: int
    cost_usd: float
    success_count: int
    failed_count: int


class RunStatsResponse(BaseModel):
    """7-day trend statistics for dashboard."""
    daily: list[DailyStats]
    total_runs: int
    total_cost_usd: float
    success_rate: float
    source: str = "backend"


@router.get("/stats", response_model=RunStatsResponse)
async def get_run_stats() -> RunStatsResponse:
    """Get 7-day run statistics for dashboard KPI sparklines."""
    daily: list[DailyStats] = []
    total_runs = 0
    total_cost = 0.0
    total_success = 0

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    DATE(started_at) AS day,
                    COUNT(*) AS run_count,
                    COALESCE(SUM(total_cost_usd), 0) AS cost_usd,
                    COUNT(*) FILTER (WHERE status = 'completed') AS success_count,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed_count
                FROM workflow_runs
                WHERE started_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(started_at)
                ORDER BY day
                """
            )
            for row in rows:
                daily.append(DailyStats(
                    date=row["day"].isoformat(),
                    run_count=row["run_count"],
                    cost_usd=float(row["cost_usd"]),
                    success_count=row["success_count"],
                    failed_count=row["failed_count"],
                ))
                total_runs += row["run_count"]
                total_cost += float(row["cost_usd"])
                total_success += row["success_count"]
    except Exception as e:
        logger.warning("run_stats_db_failed", error=str(e))

    success_rate = (total_success / total_runs * 100) if total_runs > 0 else 0.0

    return RunStatsResponse(
        daily=daily,
        total_runs=total_runs,
        total_cost_usd=total_cost,
        success_rate=round(success_rate, 1),
    )


@router.get("/{run_id}", response_model=RunItem)
async def get_run(run_id: str) -> RunItem:
    """Get a single workflow run with step details."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, workflow_name, skill_name, status,
                       started_at, completed_at, total_duration_ms, total_cost_usd
                FROM workflow_runs WHERE id = $1::uuid
                """,
                run_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Run not found")

            step_rows = await conn.fetch(
                """
                SELECT step_name, status, duration_ms, cost_usd,
                       model_used, input_tokens, output_tokens, error
                FROM step_runs WHERE workflow_run_id = $1::uuid
                ORDER BY step_index
                """,
                run_id,
            )
            steps = [
                StepRunItem(
                    step_name=sr["step_name"],
                    status=sr["status"],
                    duration_ms=sr["duration_ms"],
                    cost_usd=sr["cost_usd"] or 0.0,
                    model_used=sr["model_used"],
                    input_tokens=sr["input_tokens"],
                    output_tokens=sr["output_tokens"],
                    error=sr["error"],
                )
                for sr in step_rows
            ]

            return RunItem(
                run_id=str(row["id"]),
                workflow_name=row["workflow_name"],
                skill_name=row["skill_name"],
                status=row["status"],
                started_at=row["started_at"].isoformat() if row["started_at"] else None,
                completed_at=row["completed_at"].isoformat() if row["completed_at"] else None,
                total_duration_ms=row["total_duration_ms"],
                total_cost_usd=row["total_cost_usd"] or 0.0,
                steps=steps,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("run_detail_db_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
