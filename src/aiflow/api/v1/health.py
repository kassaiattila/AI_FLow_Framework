"""Health check endpoints.

Provides liveness, readiness, and detailed health endpoints.
Checks: PostgreSQL connection, pgvector extension, RAG collections/chunks, Redis.
"""
from __future__ import annotations

import os

import asyncpg
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from aiflow._version import __version__

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


def _get_db_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "AIFLOW_DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )


def _get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.getenv("AIFLOW_REDIS_URL", "redis://localhost:6379/0")


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


async def _check_database() -> ReadyCheck:
    """Check PostgreSQL connectivity."""
    db_url = _get_db_url()
    try:
        conn = await asyncpg.connect(db_url)
        try:
            row = await conn.fetchval("SELECT 1")
            if row == 1:
                return ReadyCheck(
                    name="database",
                    status="ok",
                    message="PostgreSQL connected",
                )
            return ReadyCheck(
                name="database",
                status="degraded",
                message="Unexpected query result",
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("health_db_check_failed", error=str(e))
        return ReadyCheck(
            name="database",
            status="error",
            message=f"Connection failed: {type(e).__name__}",
        )


async def _check_pgvector() -> ReadyCheck:
    """Check pgvector extension availability."""
    db_url = _get_db_url()
    try:
        conn = await asyncpg.connect(db_url)
        try:
            row = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            if row:
                return ReadyCheck(
                    name="pgvector",
                    status="ok",
                    message=f"pgvector v{row} installed",
                )
            return ReadyCheck(
                name="pgvector",
                status="error",
                message="pgvector extension not installed",
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("health_pgvector_check_failed", error=str(e))
        return ReadyCheck(
            name="pgvector",
            status="error",
            message=f"Check failed: {type(e).__name__}",
        )


async def _check_rag_data() -> ReadyCheck:
    """Check RAG collections and chunk counts."""
    db_url = _get_db_url()
    try:
        conn = await asyncpg.connect(db_url)
        try:
            # Check collection count
            collection_count = await conn.fetchval(
                "SELECT COUNT(DISTINCT collection) FROM rag_chunks"
            )
            chunk_count = await conn.fetchval(
                "SELECT COUNT(*) FROM rag_chunks"
            )
            return ReadyCheck(
                name="rag_data",
                status="ok",
                message=f"{collection_count} collections, {chunk_count} chunks",
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("health_rag_data_check_failed", error=str(e))
        return ReadyCheck(
            name="rag_data",
            status="error",
            message=f"Check failed: {type(e).__name__}",
        )


async def _check_redis() -> ReadyCheck:
    """Check Redis connectivity via raw socket PING."""
    redis_url = _get_redis_url()
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, socket_connect_timeout=3)
        try:
            pong = await client.ping()
            if pong:
                return ReadyCheck(
                    name="redis",
                    status="ok",
                    message="Redis connected (PONG)",
                )
            return ReadyCheck(
                name="redis",
                status="degraded",
                message="Redis did not PONG",
            )
        finally:
            await client.aclose()
    except ImportError:
        return ReadyCheck(
            name="redis",
            status="degraded",
            message="redis package not installed, skipping check",
        )
    except Exception as e:
        logger.warning("health_redis_check_failed", error=str(e))
        return ReadyCheck(
            name="redis",
            status="error",
            message=f"Connection failed: {type(e).__name__}",
        )


async def _check_langfuse() -> ReadyCheck:
    """Check Langfuse observability connectivity."""
    try:
        from aiflow.observability.tracing import get_langfuse_client

        client = get_langfuse_client()
        if client is None:
            # Check if keys are configured but client not initialized
            pk = os.getenv("AIFLOW_LANGFUSE__PUBLIC_KEY", "")
            if not pk:
                return ReadyCheck(
                    name="langfuse",
                    status="disabled",
                    message="Langfuse not configured (no API keys)",
                )
            return ReadyCheck(
                name="langfuse",
                status="disabled",
                message="Langfuse client not initialized",
            )

        auth_ok = client.auth_check()
        if auth_ok:
            return ReadyCheck(
                name="langfuse",
                status="ok",
                message="Langfuse connected",
            )
        return ReadyCheck(
            name="langfuse",
            status="error",
            message="Langfuse auth check failed",
        )
    except Exception as e:
        logger.warning("health_langfuse_check_failed", error=str(e))
        return ReadyCheck(
            name="langfuse",
            status="error",
            message=f"Check failed: {type(e).__name__}",
        )


@router.get("/health/live", response_model=LiveResponse)
async def liveness() -> LiveResponse:
    """Kubernetes liveness probe - is the process alive?"""
    return LiveResponse(status="alive")


@router.get("/health/ready", response_model=ReadyResponse)
async def readiness() -> ReadyResponse:
    """Kubernetes readiness probe - can we serve traffic?

    Runs real checks against PostgreSQL, pgvector, RAG data, and Redis.
    Returns 'ready' only when all critical checks (database) pass.
    """
    checks: list[ReadyCheck] = []

    # Database check (critical)
    checks.append(await _check_database())

    # pgvector extension check
    checks.append(await _check_pgvector())

    # RAG collections and chunks
    checks.append(await _check_rag_data())

    # Redis check
    checks.append(await _check_redis())

    # Langfuse observability check (non-critical)
    checks.append(await _check_langfuse())

    # Determine overall status: error in database = not ready
    db_check = next((c for c in checks if c.name == "database"), None)
    if db_check and db_check.status == "error":
        overall = "not_ready"
    elif any(c.status == "error" for c in checks):
        overall = "degraded"
    else:
        overall = "ready"

    return ReadyResponse(
        status=overall,
        checks=checks,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Combined health check with version and environment info."""
    ready = await readiness()
    return HealthResponse(
        status=ready.status,
        version=__version__,
        environment=os.getenv("AIFLOW_ENVIRONMENT", "development"),
        checks=ready.checks,
    )
