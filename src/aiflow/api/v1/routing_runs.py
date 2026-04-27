"""Routing-runs read API — Sprint X / SX-3.

Three GET routes scoped to ``/api/v1/routing-runs``:

* ``GET /``         — paginated list with query filters.
* ``GET /stats``    — aggregate distributions + cost/latency centiles
                      (must be declared BEFORE ``/{run_id}`` so the
                      latter's UUID-typed path param doesn't shadow it).
* ``GET /{run_id}`` — single-row detail; 404 on miss; tenant-scoped.

Auth + tenant scope: the existing
:class:`aiflow.api.middleware.AuthMiddleware` enforces JWT validity at
the edge. The router itself reads ``tenant_id`` from a query parameter
(default ``"default"``) — same pattern the surrounding emails / costs
routers use. The repository's ``get`` enforces the tenant filter at the
SQL level so a cross-tenant ID guess returns 404, not the row.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query

from aiflow.api.deps import get_pool
from aiflow.services.routing_runs.repository import (
    RoutingRunRepository,
    default_stats_window,
)
from aiflow.services.routing_runs.schemas import (
    ExtractionOutcomeAggregated,
    RoutingRunDetail,
    RoutingRunFilters,
    RoutingRunSummary,
    RoutingStatsResponse,
)

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/routing-runs", tags=["routing-runs"])


class RoutingRunListResponse(RoutingRunSummary):
    """Re-export so OpenAPI surfaces the list shape under a stable name."""

    # Empty subclass — Pydantic preserves all parent fields.


async def _repository() -> RoutingRunRepository:
    pool = await get_pool()
    return RoutingRunRepository(pool)


# ---------------------------------------------------------------------------
# GET /api/v1/routing-runs/  — paginated list
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[RoutingRunSummary])
async def list_routing_runs(
    tenant_id: Annotated[str, Query(description="Tenant scope (default 'default').")] = "default",
    intent_class: Annotated[str | None, Query(description="Filter by intent class.")] = None,
    doctype_detected: Annotated[
        str | None, Query(description="Filter by detected doctype.")
    ] = None,
    extraction_outcome: Annotated[
        ExtractionOutcomeAggregated | None,
        Query(description="Filter by aggregated extraction outcome."),
    ] = None,
    since: Annotated[datetime | None, Query(description="ISO8601 lower bound (inclusive).")] = None,
    until: Annotated[datetime | None, Query(description="ISO8601 upper bound (exclusive).")] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Page size.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset.")] = 0,
) -> list[RoutingRunSummary]:
    """List routing runs ordered ``created_at DESC``.

    All filters are AND-combined. ``limit`` is hard-capped at 200; the
    422 from FastAPI's validator is the desired response (matches the
    NEXT.md unit test ``test_get_list_rejects_limit_over_200_with_422``).
    """
    repo = await _repository()
    filters = RoutingRunFilters(
        tenant_id=tenant_id,
        intent_class=intent_class,
        doctype_detected=doctype_detected,
        extraction_outcome=extraction_outcome,
        since=since,
        until=until,
    )
    return await repo.list(filters=filters, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# GET /api/v1/routing-runs/stats  — aggregate
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=RoutingStatsResponse)
async def get_routing_runs_stats(
    tenant_id: Annotated[str, Query(description="Tenant scope.")] = "default",
    since: Annotated[
        datetime | None, Query(description="ISO8601 window start (default 7 days ago).")
    ] = None,
    until: Annotated[
        datetime | None, Query(description="ISO8601 window end (default now).")
    ] = None,
) -> RoutingStatsResponse:
    """Aggregate per-doctype + per-outcome + per-path counts plus
    mean cost and latency centiles for the supplied window.

    When both ``since`` and ``until`` are omitted the window defaults
    to the last 7 days. Empty windows return ``total_runs=0`` with
    empty distribution lists and zeroed centiles."""
    repo = await _repository()
    if since is None or until is None:
        default_since, default_until = default_stats_window()
        if since is None:
            since = default_since
        if until is None:
            until = default_until
    if since >= until:
        raise HTTPException(status_code=400, detail="`since` must be < `until`")
    return await repo.aggregate_stats(tenant_id=tenant_id, since=since, until=until)


# ---------------------------------------------------------------------------
# GET /api/v1/routing-runs/{run_id}  — detail
# ---------------------------------------------------------------------------


@router.get("/{run_id}", response_model=RoutingRunDetail)
async def get_routing_run(
    run_id: UUID,
    tenant_id: Annotated[str, Query(description="Tenant scope.")] = "default",
) -> RoutingRunDetail:
    """Detail row scoped to ``tenant_id``. 404 on miss OR cross-tenant
    ID collision (no leakage)."""
    repo = await _repository()
    row = await repo.get(run_id, tenant_id=tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Routing run not found: {run_id}")
    return row
