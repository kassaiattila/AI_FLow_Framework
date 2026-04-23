"""Workflow run listing and detail endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool
from aiflow.observability.tracing import get_langfuse_client

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
    trace_id: str | None = None
    trace_url: str | None = None
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
                       r.started_at, r.completed_at, r.total_duration_ms, r.total_cost_usd,
                       r.trace_id, r.trace_url
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
                    steps_by_run[rid].append(
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
                    )

            for row in rows:
                rid = str(row["id"])
                runs.append(
                    RunItem(
                        run_id=rid,
                        workflow_name=row["workflow_name"],
                        skill_name=row["skill_name"],
                        status=row["status"],
                        started_at=row["started_at"].isoformat() if row["started_at"] else None,
                        completed_at=row["completed_at"].isoformat()
                        if row["completed_at"]
                        else None,
                        total_duration_ms=row["total_duration_ms"],
                        total_cost_usd=row["total_cost_usd"] or 0.0,
                        trace_id=row["trace_id"],
                        trace_url=row["trace_url"],
                        steps=steps_by_run.get(rid, []),
                    )
                )
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
                daily.append(
                    DailyStats(
                        date=row["day"].isoformat(),
                        run_count=row["run_count"],
                        cost_usd=float(row["cost_usd"]),
                        success_count=row["success_count"],
                        failed_count=row["failed_count"],
                    )
                )
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
                       started_at, completed_at, total_duration_ms, total_cost_usd,
                       trace_id, trace_url
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
                trace_id=row["trace_id"],
                trace_url=row["trace_url"],
                steps=steps,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("run_detail_db_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Langfuse trace proxy (S111)
# ---------------------------------------------------------------------------


class TraceSpan(BaseModel):
    """Single span in a Langfuse trace, expressed relative to trace start."""

    id: str
    name: str
    start_ms: int
    duration_ms: int
    status: str = "ok"
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    model: str | None = None
    children: list[TraceSpan] = Field(default_factory=list)


class TraceResponse(BaseModel):
    """Langfuse trace tree for a workflow run, suitable for UI drill-down."""

    trace_id: str
    run_id: str
    total_duration_ms: int
    total_cost_usd: float
    root_spans: list[TraceSpan]
    source: str = "backend"


def _build_trace_tree(trace_id: str, run_id: str, trace_obj: Any) -> TraceResponse:
    """Convert a Langfuse ``TraceWithFullDetails`` into our tree response."""
    observations = list(getattr(trace_obj, "observations", []) or [])

    start_times: list[datetime] = [o.start_time for o in observations if o.start_time]
    trace_start = (
        min(start_times)
        if start_times
        else datetime.now(observations[0].start_time.tzinfo)
        if observations
        else datetime.utcnow()
    )

    span_by_id: dict[str, TraceSpan] = {}
    parents: dict[str, str | None] = {}

    for obs in observations:
        start_ms = (
            int((obs.start_time - trace_start).total_seconds() * 1000) if obs.start_time else 0
        )
        if obs.end_time and obs.start_time:
            duration_ms = int((obs.end_time - obs.start_time).total_seconds() * 1000)
        else:
            duration_ms = 0

        usage = obs.usage_details or {}
        input_tokens = usage.get("input") or (obs.usage.input if obs.usage else None)
        output_tokens = usage.get("output") or (obs.usage.output if obs.usage else None)
        cost_usd = obs.calculated_total_cost
        if cost_usd is None and obs.cost_details:
            cost_usd = sum(v for v in obs.cost_details.values() if isinstance(v, int | float))

        level = getattr(obs.level, "value", str(obs.level)) if obs.level else "DEFAULT"
        status = "error" if level == "ERROR" or obs.status_message else "ok"

        span_by_id[obs.id] = TraceSpan(
            id=obs.id,
            name=obs.name or obs.type,
            start_ms=max(0, start_ms),
            duration_ms=max(0, duration_ms),
            status=status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(cost_usd) if cost_usd is not None else None,
            model=obs.model,
            children=[],
        )
        parents[obs.id] = obs.parent_observation_id

    roots: list[TraceSpan] = []
    for obs_id, span in span_by_id.items():
        parent_id = parents.get(obs_id)
        if parent_id and parent_id in span_by_id:
            span_by_id[parent_id].children.append(span)
        else:
            roots.append(span)

    roots.sort(key=lambda s: s.start_ms)
    for span in span_by_id.values():
        span.children.sort(key=lambda s: s.start_ms)

    total_duration_ms = 0
    if getattr(trace_obj, "latency", None):
        total_duration_ms = int(trace_obj.latency * 1000)
    elif observations:
        end_times = [o.end_time for o in observations if o.end_time]
        if end_times:
            total_duration_ms = int((max(end_times) - trace_start).total_seconds() * 1000)

    total_cost_usd = float(getattr(trace_obj, "total_cost", None) or 0.0)
    if total_cost_usd == 0.0:
        total_cost_usd = sum(s.cost_usd or 0.0 for s in span_by_id.values())

    return TraceResponse(
        trace_id=trace_id,
        run_id=run_id,
        total_duration_ms=max(0, total_duration_ms),
        total_cost_usd=round(total_cost_usd, 6),
        root_spans=roots,
    )


@router.get("/{run_id}/trace", response_model=TraceResponse)
async def get_run_trace(run_id: str) -> TraceResponse:
    """Proxy the Langfuse trace for a workflow run.

    Returns the span tree (with timing, token, cost breakdown) associated with
    the run's ``trace_id``. Response shape is stable across Langfuse SDK bumps;
    the UI relies on it directly.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT trace_id FROM workflow_runs WHERE id = $1::uuid",
                run_id,
            )
    except Exception as e:
        logger.warning("run_trace_db_failed", error=str(e), run_id=run_id)
        raise HTTPException(status_code=500, detail="run lookup failed") from e

    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    trace_id = row["trace_id"]
    if not trace_id:
        raise HTTPException(
            status_code=404,
            detail="Run has no trace_id (Langfuse not recorded)",
        )

    client = get_langfuse_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Langfuse not configured")

    try:
        trace_obj = client.api.trace.get(trace_id)
    except Exception as e:
        logger.warning("langfuse_trace_fetch_failed", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=502, detail=f"Langfuse fetch failed: {e}") from e

    return _build_trace_tree(trace_id=trace_id, run_id=run_id, trace_obj=trace_obj)
