"""Service management API — discovery, health, cache stats, rate limit info."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aiflow.services import (
    CacheConfig,
    CacheService,
    RateLimiterConfig,
    RateLimiterService,
    RateLimitRule,
    ResilienceService,
    SchemaRegistryConfig,
    SchemaRegistryService,
    ServiceRegistry,
)

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/services", tags=["services"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ServiceInfo(BaseModel):
    name: str
    status: str
    description: str


class ServiceListResponse(BaseModel):
    services: list[ServiceInfo]
    count: int
    source: str = "backend"


class ServiceHealthResponse(BaseModel):
    status: str
    services: dict[str, Any]
    source: str = "backend"


class CacheStatsResponse(BaseModel):
    stats: dict[str, Any]
    source: str = "backend"


class CacheInvalidateResponse(BaseModel):
    deleted: int
    scope: str
    source: str = "backend"


class RateLimitInfoResponse(BaseModel):
    source: str = "backend"

    class Config:
        extra = "allow"


class ResetResponse(BaseModel):
    reset: bool = True
    key: str
    source: str = "backend"


class CircuitStateResponse(BaseModel):
    source: str = "backend"

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# Module-level singleton (mutable container avoids `global` keyword)
# ---------------------------------------------------------------------------

_state: dict[str, Any] = {}


async def _get_registry() -> ServiceRegistry:
    """Lazy-init service registry with all F0 infra services."""
    if "registry" in _state:
        return _state["registry"]

    registry = ServiceRegistry()

    from aiflow.core.config import get_settings

    settings = get_settings()

    # Cache service
    cache = CacheService(
        CacheConfig(redis_url=settings.redis.url)
    )
    registry.register(cache)

    # Rate limiter
    rate_limiter = RateLimiterService(
        RateLimiterConfig(redis_url=settings.redis.url)
    )
    registry.register(rate_limiter)

    # Resilience (no external deps)
    resilience = ResilienceService()
    registry.register(resilience)

    # Schema registry
    schema_reg = SchemaRegistryService(
        SchemaRegistryConfig(skills_dir="skills")
    )
    registry.register(schema_reg)

    # Start all services
    results = await registry.start_all()
    logger.info("services_initialized", results=results)
    _state["registry"] = registry

    return registry


# --- Discovery endpoints ---


@router.get("/", response_model=ServiceListResponse)
async def list_services() -> dict[str, Any]:
    """List all registered services with their status."""
    registry = await _get_registry()
    services = registry.list_services()
    return {
        "services": [
            {
                "name": svc.name,
                "status": svc.status.value,
                "description": svc.description,
            }
            for svc in services
        ],
        "count": len(services),
        "source": "backend",
    }


@router.get("/health", response_model=ServiceHealthResponse)
async def service_health() -> dict[str, Any]:
    """Health check all services."""
    registry = await _get_registry()
    health = await registry.health_check_all()
    all_healthy = all(v.get("healthy", False) for v in health.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": health,
        "source": "backend",
    }


# --- Cache endpoints ---


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    registry = await _get_registry()
    cache = registry.get("cache")
    if not isinstance(cache, CacheService):
        raise HTTPException(status_code=503, detail="Cache service not available")
    stats = await cache.get_stats()
    return {"stats": stats, "source": "backend"}


@router.post("/cache/invalidate", response_model=CacheInvalidateResponse)
async def cache_invalidate(scope: str = "all") -> dict[str, Any]:
    """Invalidate cache entries.

    scope: "all", "emb", "llm", "vec", or "collection:{name}"
    """
    registry = await _get_registry()
    cache = registry.get("cache")
    if not isinstance(cache, CacheService):
        raise HTTPException(status_code=503, detail="Cache service not available")

    if scope == "all":
        total = 0
        for ns in ("emb", "llm", "vec"):
            total += await cache.invalidate_namespace(ns)
        return {"deleted": total, "scope": scope, "source": "backend"}
    elif scope.startswith("collection:"):
        collection = scope.split(":", 1)[1]
        deleted = await cache.invalidate_collection(collection)
        return {"deleted": deleted, "scope": scope, "source": "backend"}
    elif scope in ("emb", "llm", "vec"):
        deleted = await cache.invalidate_namespace(scope)
        return {"deleted": deleted, "scope": scope, "source": "backend"}
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope: {scope}. Use 'all', 'emb', 'llm', 'vec', or 'collection:{{name}}'",
        )


# --- Rate limiter endpoints ---


@router.get("/rate-limit/{key}", response_model=RateLimitInfoResponse)
async def rate_limit_info(key: str) -> dict[str, Any]:
    """Get rate limit status for a key."""
    registry = await _get_registry()
    rl = registry.get("rate_limiter")
    if not isinstance(rl, RateLimiterService):
        raise HTTPException(status_code=503, detail="Rate limiter not available")
    info = await rl.get_remaining(key)
    return {**info, "source": "backend"}


@router.post("/rate-limit/{key}/reset", response_model=ResetResponse)
async def rate_limit_reset(key: str) -> dict[str, Any]:
    """Reset rate limit counter for a key."""
    registry = await _get_registry()
    rl = registry.get("rate_limiter")
    if not isinstance(rl, RateLimiterService):
        raise HTTPException(status_code=503, detail="Rate limiter not available")
    await rl.reset(key)
    return {"reset": True, "key": key, "source": "backend"}


# --- Resilience endpoints ---


@router.get("/resilience/{key}", response_model=CircuitStateResponse)
async def circuit_state(key: str) -> dict[str, Any]:
    """Get circuit breaker state for a service key."""
    registry = await _get_registry()
    res = registry.get("resilience")
    if not isinstance(res, ResilienceService):
        raise HTTPException(status_code=503, detail="Resilience service not available")
    state = res.get_circuit_state(key)
    return {**state, "source": "backend"}


@router.post("/resilience/{key}/reset", response_model=ResetResponse)
async def circuit_reset(key: str) -> dict[str, Any]:
    """Reset circuit breaker for a service key."""
    registry = await _get_registry()
    res = registry.get("resilience")
    if not isinstance(res, ResilienceService):
        raise HTTPException(status_code=503, detail="Resilience service not available")
    res.reset_circuit(key)
    return {"reset": True, "key": key, "source": "backend"}
