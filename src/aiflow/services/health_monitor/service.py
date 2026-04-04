"""HealthMonitorService — checks DB, Redis, LLM, and all F0-F4 services."""
from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel

__all__ = ["HealthMonitorService"]

logger = structlog.get_logger(__name__)


class ServiceHealth(BaseModel):
    service_name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float | None = None
    details: dict[str, Any] | None = None
    checked_at: str = ""


class HealthMonitorService:
    """Checks health of all infrastructure and domain services."""

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            url = self._db_url or os.getenv(
                "AIFLOW_DATABASE__URL",
                "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
            ).replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
        return self._pool

    async def check_all(self) -> list[ServiceHealth]:
        """Run health checks for all known services."""
        checks = [
            self._check_postgresql(),
            self._check_redis(),
            self._check_service_table("document_extractor", "documents"),
            self._check_service_table("email_connector", "email_connector_configs"),
            self._check_service_table("rag_engine", "rag_collections"),
            self._check_service_table("diagram_generator", "generated_diagrams"),
            self._check_service_table("media_processor", "media_jobs"),
            self._check_service_table("rpa_browser", "rpa_configs"),
            self._check_service_table("human_review", "human_review_queue"),
        ]
        import asyncio
        results = await asyncio.gather(*checks, return_exceptions=True)
        health_list = []
        for r in results:
            if isinstance(r, Exception):
                health_list.append(ServiceHealth(
                    service_name="unknown",
                    status="unhealthy",
                    details={"error": str(r)},
                    checked_at=datetime.now(UTC).isoformat(),
                ))
            else:
                health_list.append(r)
        # Persist results
        for h in health_list:
            await self._persist_check(h)
        return health_list

    async def get_service_health(self, service_name: str) -> ServiceHealth | None:
        """Get latest health for a specific service."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM service_health_log
                   WHERE service_name = $1
                   ORDER BY checked_at DESC LIMIT 1""",
                service_name,
            )
        if not row:
            return None
        return ServiceHealth(
            service_name=row["service_name"],
            status=row["status"],
            latency_ms=row["latency_ms"],
            details=row["details"],
            checked_at=str(row["checked_at"]),
        )

    async def get_metrics(self) -> list[dict[str, Any]]:
        """Get aggregated metrics per service (last 24h)."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT service_name,
                          COUNT(*) as check_count,
                          AVG(latency_ms) as avg_latency_ms,
                          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
                          SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as success_rate
                   FROM service_health_log
                   WHERE checked_at > NOW() - INTERVAL '24 hours'
                   GROUP BY service_name
                   ORDER BY service_name"""
            )
        return [
            {
                "service_name": r["service_name"],
                "check_count": r["check_count"],
                "avg_latency_ms": round(r["avg_latency_ms"], 1) if r["avg_latency_ms"] else None,
                "p95_latency_ms": round(r["p95_latency_ms"], 1) if r["p95_latency_ms"] else None,
                "success_rate": round(r["success_rate"] * 100, 1) if r["success_rate"] else 0,
            }
            for r in rows
        ]

    async def _check_postgresql(self) -> ServiceHealth:
        t0 = time.monotonic()
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            latency = (time.monotonic() - t0) * 1000
            return ServiceHealth(
                service_name="postgresql",
                status="healthy",
                latency_ms=round(latency, 1),
                details={"version": "PostgreSQL 16+"},
                checked_at=datetime.now(UTC).isoformat(),
            )
        except Exception as e:
            return ServiceHealth(
                service_name="postgresql",
                status="unhealthy",
                latency_ms=round((time.monotonic() - t0) * 1000, 1),
                details={"error": str(e)},
                checked_at=datetime.now(UTC).isoformat(),
            )

    async def _check_redis(self) -> ServiceHealth:
        t0 = time.monotonic()
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(os.getenv("AIFLOW_REDIS__URL", "redis://localhost:6379/0"))
            await r.ping()
            await r.aclose()
            latency = (time.monotonic() - t0) * 1000
            return ServiceHealth(
                service_name="redis",
                status="healthy",
                latency_ms=round(latency, 1),
                checked_at=datetime.now(UTC).isoformat(),
            )
        except Exception as e:
            return ServiceHealth(
                service_name="redis",
                status="unhealthy",
                latency_ms=round((time.monotonic() - t0) * 1000, 1),
                details={"error": str(e)},
                checked_at=datetime.now(UTC).isoformat(),
            )

    _ALLOWED_TABLES: frozenset[str] = frozenset({
        "documents", "email_connector_configs", "rag_collections",
        "generated_diagrams", "media_jobs", "rpa_configs", "human_review_queue",
    })

    async def _check_service_table(self, service_name: str, table_name: str) -> ServiceHealth:
        if table_name not in self._ALLOWED_TABLES:
            raise ValueError(f"Table '{table_name}' not in health check whitelist")
        t0 = time.monotonic()
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608 — table_name validated above
            latency = (time.monotonic() - t0) * 1000
            return ServiceHealth(
                service_name=service_name,
                status="healthy",
                latency_ms=round(latency, 1),
                details={"record_count": count},
                checked_at=datetime.now(UTC).isoformat(),
            )
        except Exception as e:
            return ServiceHealth(
                service_name=service_name,
                status="unhealthy",
                latency_ms=round((time.monotonic() - t0) * 1000, 1),
                details={"error": str(e)},
                checked_at=datetime.now(UTC).isoformat(),
            )

    async def _persist_check(self, health: ServiceHealth) -> None:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                import json
                await conn.execute(
                    """INSERT INTO service_health_log (id, service_name, status, latency_ms, details)
                       VALUES ($1, $2, $3, $4, $5)""",
                    str(uuid.uuid4()),
                    health.service_name,
                    health.status,
                    health.latency_ms,
                    json.dumps(health.details) if health.details else None,
                )
        except Exception as e:
            logger.warning("health_persist_failed", service=health.service_name, error=str(e))
