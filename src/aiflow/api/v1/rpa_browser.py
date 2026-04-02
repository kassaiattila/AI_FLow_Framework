"""RPA Browser API — config CRUD + execute + logs."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from functools import cache
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/rpa", tags=["rpa"])


@cache
def _get_service():
    from aiflow.services.rpa_browser import RPABrowserService
    return RPABrowserService()


class ConfigCreateRequest(BaseModel):
    name: str
    description: str | None = None
    yaml_config: str
    target_url: str | None = None
    schedule_cron: str | None = None


class ConfigResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    yaml_config: str
    target_url: str | None = None
    is_active: bool = True
    schedule_cron: str | None = None
    created_at: str = ""
    source: str = "backend"


class ConfigListResponse(BaseModel):
    configs: list[ConfigResponse]
    total: int
    source: str = "backend"


class ExecutionResponse(BaseModel):
    id: str
    config_id: str
    status: str
    steps_total: int | None = None
    steps_completed: int = 0
    results: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float | None = None
    started_at: str = ""
    completed_at: str | None = None
    source: str = "backend"


class ExecutionListResponse(BaseModel):
    executions: list[ExecutionResponse]
    total: int
    source: str = "backend"


@router.get("/configs", response_model=ConfigListResponse)
async def list_configs():
    svc = _get_service()
    configs = await svc.list_configs()
    return ConfigListResponse(
        configs=[ConfigResponse(**{k: v for k, v in c.model_dump().items() if k in ConfigResponse.model_fields}, source="backend") for c in configs],
        total=len(configs),
    )


@router.post("/configs", response_model=ConfigResponse, status_code=201)
async def create_config(request: ConfigCreateRequest):
    svc = _get_service()
    try:
        cfg = await svc.create_config(**request.model_dump())
        return ConfigResponse(**{k: v for k, v in cfg.model_dump().items() if k in ConfigResponse.model_fields}, source="backend")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{config_id}", response_model=ConfigResponse)
async def get_config(config_id: str):
    svc = _get_service()
    cfg = await svc.get_config(config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigResponse(**{k: v for k, v in cfg.model_dump().items() if k in ConfigResponse.model_fields}, source="backend")


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str):
    svc = _get_service()
    deleted = await svc.delete_config(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"deleted": True, "source": "backend"}


@router.post("/configs/{config_id}/execute", response_model=ExecutionResponse)
async def execute_config(config_id: str):
    svc = _get_service()
    try:
        result = await svc.execute(config_id)
        return ExecutionResponse(**{k: v for k, v in result.model_dump().items() if k in ExecutionResponse.model_fields}, source="backend")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=ExecutionListResponse)
async def list_executions(config_id: str | None = None, limit: int = 50):
    svc = _get_service()
    execs = await svc.list_executions(config_id=config_id, limit=limit)
    return ExecutionListResponse(
        executions=[ExecutionResponse(**{k: v for k, v in e.model_dump().items() if k in ExecutionResponse.model_fields}, source="backend") for e in execs],
        total=len(execs),
    )
