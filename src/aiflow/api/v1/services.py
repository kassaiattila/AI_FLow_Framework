"""Service management API — discovery, health, cache stats, rate limit info."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

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

# Global service registry — initialized on first request
_registry: ServiceRegistry | None = None
_initialized = False


async def _get_registry() -> ServiceRegistry:
    """Lazy-init service registry with all F0 infra services."""
    global _registry, _initialized
    if _registry is not None and _initialized:
        return _registry

    _registry = ServiceRegistry()

    from aiflow.core.config import get_settings

    settings = get_settings()

    # Cache service
    cache = CacheService(
        CacheConfig(redis_url=settings.redis.url)
    )
    _registry.register(cache)

    # Rate limiter
    rate_limiter = RateLimiterService(
        RateLimiterConfig(redis_url=settings.redis.url)
    )
    _registry.register(rate_limiter)

    # Resilience (no external deps)
    resilience = ResilienceService()
    _registry.register(resilience)

    # Schema registry
    schema_reg = SchemaRegistryService(
        SchemaRegistryConfig(skills_dir="skills")
    )
    _registry.register(schema_reg)

    # Start all services
    results = await _registry.start_all()
    logger.info("services_initialized", results=results)
    _initialized = True

    return _registry


# --- Discovery endpoints ---


@router.get("/")
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


@router.get("/health")
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


@router.get("/cache/stats")
async def cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    registry = await _get_registry()
    cache = registry.get("cache")
    if not isinstance(cache, CacheService):
        raise HTTPException(status_code=503, detail="Cache service not available")
    stats = await cache.get_stats()
    return {"stats": stats, "source": "backend"}


@router.post("/cache/invalidate")
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


@router.get("/rate-limit/{key}")
async def rate_limit_info(key: str) -> dict[str, Any]:
    """Get rate limit status for a key."""
    registry = await _get_registry()
    rl = registry.get("rate_limiter")
    if not isinstance(rl, RateLimiterService):
        raise HTTPException(status_code=503, detail="Rate limiter not available")
    info = await rl.get_remaining(key)
    return {**info, "source": "backend"}


@router.post("/rate-limit/{key}/reset")
async def rate_limit_reset(key: str) -> dict[str, Any]:
    """Reset rate limit counter for a key."""
    registry = await _get_registry()
    rl = registry.get("rate_limiter")
    if not isinstance(rl, RateLimiterService):
        raise HTTPException(status_code=503, detail="Rate limiter not available")
    await rl.reset(key)
    return {"reset": True, "key": key, "source": "backend"}


# --- Resilience endpoints ---


@router.get("/resilience/{key}")
async def circuit_state(key: str) -> dict[str, Any]:
    """Get circuit breaker state for a service key."""
    registry = await _get_registry()
    res = registry.get("resilience")
    if not isinstance(res, ResilienceService):
        raise HTTPException(status_code=503, detail="Resilience service not available")
    state = res.get_circuit_state(key)
    return {**state, "source": "backend"}


@router.post("/resilience/{key}/reset")
async def circuit_reset(key: str) -> dict[str, Any]:
    """Reset circuit breaker for a service key."""
    registry = await _get_registry()
    res = registry.get("resilience")
    if not isinstance(res, ResilienceService):
        raise HTTPException(status_code=503, detail="Resilience service not available")
    res.reset_circuit(key)
    return {"reset": True, "key": key, "source": "backend"}
