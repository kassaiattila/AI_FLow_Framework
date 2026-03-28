"""Health check endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from aiflow._version import __version__

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


class LiveResponse(BaseModel):
    """Liveness probe response."""
    status: str = "alive"


class ReadyCheck(BaseModel):
    """Individual readiness check."""
    name: str
    status: str
    message: str | None = None


class ReadyResponse(BaseModel):
    """Readiness probe response."""
    status: str
    checks: list[ReadyCheck]


class HealthResponse(BaseModel):
    """Combined health response."""
    status: str
    version: str
    environment: str
    checks: list[ReadyCheck]


@router.get("/health/live", response_model=LiveResponse)
async def liveness() -> LiveResponse:
    """Kubernetes liveness probe - is the process alive?"""
    return LiveResponse(status="alive")


@router.get("/health/ready", response_model=ReadyResponse)
async def readiness() -> ReadyResponse:
    """Kubernetes readiness probe - can we serve traffic?"""
    checks: list[ReadyCheck] = []

    # Database check (placeholder)
    checks.append(ReadyCheck(
        name="database",
        status="ok",
        message="placeholder - not connected",
    ))

    # Redis check (placeholder)
    checks.append(ReadyCheck(
        name="redis",
        status="ok",
        message="placeholder - not connected",
    ))

    all_ok = all(c.status == "ok" for c in checks)
    return ReadyResponse(
        status="ready" if all_ok else "degraded",
        checks=checks,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Combined health check with version and environment info."""
    ready = await readiness()
    return HealthResponse(
        status=ready.status,
        version=__version__,
        environment="development",
        checks=ready.checks,
    )
