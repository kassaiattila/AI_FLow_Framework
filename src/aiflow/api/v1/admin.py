"""Admin API — health monitoring + audit trail + metrics."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_health_service = None
_audit_service = None


def _get_health():
    global _health_service
    if _health_service is None:
        from aiflow.services.health_monitor import HealthMonitorService
        _health_service = HealthMonitorService()
    return _health_service


def _get_audit():
    global _audit_service
    if _audit_service is None:
        from aiflow.services.audit import AuditTrailService
        _audit_service = AuditTrailService()
    return _audit_service


# --- Health ---

class ServiceHealthResponse(BaseModel):
    service_name: str
    status: str
    latency_ms: float | None = None
    details: dict[str, Any] | None = None
    checked_at: str = ""


class HealthListResponse(BaseModel):
    services: list[ServiceHealthResponse]
    total: int
    overall_status: str
    source: str = "backend"


class MetricsResponse(BaseModel):
    metrics: list[dict[str, Any]]
    source: str = "backend"


@router.get("/health", response_model=HealthListResponse)
async def check_all_health():
    svc = _get_health()
    results = await svc.check_all()
    overall = "healthy"
    for r in results:
        if r.status == "unhealthy":
            overall = "unhealthy"
            break
        if r.status == "degraded":
            overall = "degraded"
    return HealthListResponse(
        services=[ServiceHealthResponse(**r.model_dump()) for r in results],
        total=len(results),
        overall_status=overall,
    )


@router.get("/health/{service_name}", response_model=ServiceHealthResponse)
async def get_service_health(service_name: str):
    svc = _get_health()
    result = await svc.get_service_health(service_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"No health data for {service_name}")
    return ServiceHealthResponse(**result.model_dump())


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    svc = _get_health()
    metrics = await svc.get_metrics()
    return MetricsResponse(metrics=metrics)


# --- Audit ---

class AuditEntryResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    user_id: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: str = ""
    source: str = "backend"


class AuditListResponse(BaseModel):
    entries: list[AuditEntryResponse]
    total: int
    source: str = "backend"


@router.get("/audit", response_model=AuditListResponse)
async def list_audit(
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(50, le=500),
):
    svc = _get_audit()
    entries = await svc.list_entries(action=action, entity_type=entity_type, user_id=user_id, limit=limit)
    return AuditListResponse(
        entries=[AuditEntryResponse(**e.model_dump(), source="backend") for e in entries],
        total=len(entries),
    )


@router.get("/audit/{entry_id}", response_model=AuditEntryResponse)
async def get_audit_entry(entry_id: str):
    svc = _get_audit()
    entry = await svc.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return AuditEntryResponse(**entry.model_dump(), source="backend")
