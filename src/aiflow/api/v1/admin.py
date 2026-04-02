"""Admin API — health monitoring + audit trail + metrics + user/key management."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import bcrypt
import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from functools import cache

from aiflow.api.deps import get_engine

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@cache
def _get_health():
    from aiflow.services.health_monitor import HealthMonitorService
    return HealthMonitorService()


@cache
def _get_audit():
    from aiflow.services.audit import AuditTrailService
    return AuditTrailService()


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


# --- Users ---

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    team_id: str | None = None
    last_login_at: str | None = None
    created_at: str = ""


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    source: str = "backend"


class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str
    role: str = "viewer"


@router.get("/users", response_model=UserListResponse)
async def list_users():
    engine = await get_engine()
    from sqlalchemy import text
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT id, email, name, role, is_active, team_id, last_login_at, created_at "
            "FROM users ORDER BY created_at DESC"
        ))
        rows = result.fetchall()
    users = [
        UserResponse(
            id=str(r[0]), email=r[1], name=r[2], role=r[3],
            is_active=r[4], team_id=str(r[5]) if r[5] else None,
            last_login_at=str(r[6]) if r[6] else None,
            created_at=str(r[7]) if r[7] else "",
        )
        for r in rows
    ]
    return UserListResponse(users=users, total=len(users))


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(req: CreateUserRequest):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    password_hash = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    engine = await get_engine()
    from sqlalchemy import text
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO users (id, email, name, role, password_hash, is_active, created_at, updated_at) "
            "VALUES (:id, :email, :name, :role, :password_hash, true, :now, :now)"
        ), {"id": user_id, "email": req.email, "name": req.name, "role": req.role,
            "password_hash": password_hash, "now": now})
    logger.info("user_created", user_id=str(user_id), email=req.email)
    return UserResponse(id=str(user_id), email=req.email, name=req.name, role=req.role, is_active=True, created_at=now.isoformat())


# --- API Keys ---

API_KEY_PREFIX = "aiflow_sk_"


class APIKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    user_id: str | None = None
    created_at: str = ""
    last_used_at: str | None = None
    is_active: bool = True


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyResponse]
    total: int
    source: str = "backend"


class APIKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key: str
    prefix: str
    source: str = "backend"


class CreateAPIKeyRequest(BaseModel):
    name: str
    user_id: str | None = None


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys():
    engine = await get_engine()
    from sqlalchemy import text
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT id, name, prefix, user_id, created_at, last_used_at, is_active "
            "FROM api_keys ORDER BY created_at DESC"
        ))
        rows = result.fetchall()
    keys = [
        APIKeyResponse(
            id=str(r[0]), name=r[1], prefix=r[2],
            user_id=str(r[3]) if r[3] else None,
            created_at=str(r[4]) if r[4] else "",
            last_used_at=str(r[5]) if r[5] else None,
            is_active=r[6],
        )
        for r in rows
    ]
    return APIKeyListResponse(keys=keys, total=len(keys))


@router.post("/api-keys", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(req: CreateAPIKeyRequest):
    raw_key = secrets.token_urlsafe(32)
    full_key = f"{API_KEY_PREFIX}{raw_key}"
    prefix = full_key[:16]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_id = uuid.uuid4()
    now = datetime.now(UTC)

    engine = await get_engine()
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO api_keys (id, name, prefix, key_hash, user_id, is_active, created_at) "
            "VALUES (:id, :name, :prefix, :key_hash, :user_id, true, :now)"
        ), {"id": key_id, "name": req.name, "prefix": prefix, "key_hash": key_hash,
            "user_id": uuid.UUID(req.user_id) if req.user_id else None, "now": now})

    logger.info("api_key_created", key_id=str(key_id), name=req.name, prefix=prefix)
    return APIKeyCreatedResponse(id=str(key_id), name=req.name, key=full_key, prefix=prefix)


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(key_id: str):
    engine = await get_engine()
    from sqlalchemy import text
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "DELETE FROM api_keys WHERE id = :id"
        ), {"id": key_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="API key not found")
    logger.info("api_key_deleted", key_id=key_id)
