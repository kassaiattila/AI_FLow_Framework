"""Data Router API — filter items, route files, move files."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/data-router", tags=["data-router"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class FilterRequest(BaseModel):
    items: list[dict[str, Any]] = Field(..., min_length=1)
    condition: str = Field(..., min_length=1)


class FilterResponse(BaseModel):
    filtered_items: list[dict[str, Any]]
    total: int
    matched: int
    source: str = "backend"


class RoutingRuleInput(BaseModel):
    condition: str
    action: str
    config: dict[str, Any] = Field(default_factory=dict)


class RouteRequest(BaseModel):
    files: list[dict[str, Any]] = Field(..., min_length=1)
    rules: list[RoutingRuleInput] = Field(..., min_length=1)


class RoutedFileItem(BaseModel):
    file_path: str
    target_path: str | None = None
    rule_matched: str | None = None
    action: str = ""
    success: bool = True
    error: str | None = None


class RouteResponse(BaseModel):
    routed_files: list[RoutedFileItem]
    total: int
    success_count: int
    failed_count: int
    source: str = "backend"


class MoveRequest(BaseModel):
    file_path: str
    target_dir_template: str
    data: dict[str, Any] = Field(default_factory=dict)


class MoveResponse(BaseModel):
    file_path: str
    target_path: str | None = None
    success: bool
    error: str | None = None
    source: str = "backend"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/filter", response_model=FilterResponse)
async def filter_items(req: FilterRequest) -> FilterResponse:
    """Filter items by a Jinja2 condition expression."""
    from aiflow.services.data_router.service import (
        DataRouterConfig,
        DataRouterService,
    )

    svc = DataRouterService(config=DataRouterConfig())
    await svc.start()

    result = await svc.filter(items=req.items, condition=req.condition)
    return FilterResponse(
        filtered_items=result.filtered_items,
        total=result.total,
        matched=result.matched,
    )


@router.post("/route", response_model=RouteResponse)
async def route_files(req: RouteRequest) -> RouteResponse:
    """Route files according to rules (first match wins)."""
    from aiflow.services.data_router.service import (
        DataRouterConfig,
        DataRouterService,
        RoutingRule,
    )

    svc = DataRouterService(config=DataRouterConfig())
    await svc.start()

    rules = [
        RoutingRule(condition=r.condition, action=r.action, config=r.config)
        for r in req.rules
    ]
    results = await svc.route_files(files=req.files, rules=rules)

    routed = [
        RoutedFileItem(
            file_path=r.file_path,
            target_path=r.target_path,
            rule_matched=r.rule_matched,
            action=r.action,
            success=r.success,
            error=r.error,
        )
        for r in results
    ]
    ok = sum(1 for r in results if r.success)
    fail = sum(1 for r in results if not r.success)
    return RouteResponse(
        routed_files=routed,
        total=len(results),
        success_count=ok,
        failed_count=fail,
    )


@router.post("/move", response_model=MoveResponse)
async def move_file(req: MoveRequest) -> MoveResponse:
    """Move a file to a template-expanded target directory."""
    from aiflow.services.data_router.service import (
        DataRouterConfig,
        DataRouterService,
    )

    svc = DataRouterService(config=DataRouterConfig())
    await svc.start()

    result = await svc.move_to_dir(
        file_path=req.file_path,
        target_dir_template=req.target_dir_template,
        data=req.data,
    )
    return MoveResponse(
        file_path=result.file_path,
        target_path=result.target_path,
        success=result.success,
        error=result.error,
    )
