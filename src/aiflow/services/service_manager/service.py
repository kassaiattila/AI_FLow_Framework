"""Service manager — lifecycle, health, metrics, config for all services."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text

from aiflow.services.base import BaseService, ServiceConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "ServiceDetail",
    "ServiceManagerConfig",
    "ServiceManagerService",
    "ServiceMetrics",
    "ServiceSummary",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ServiceSummary(BaseModel):
    """Summary info for one service."""

    name: str
    status: str
    description: str = ""
    has_adapter: bool = False


class ServiceDetail(BaseModel):
    """Detailed info for one service."""

    name: str
    status: str
    description: str = ""
    has_adapter: bool = False
    adapter_methods: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    pipelines_using: list[str] = Field(default_factory=list)


class ServiceMetrics(BaseModel):
    """Aggregated metrics for a service over a period."""

    service_name: str
    period: str = "24h"
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: int | None = None
    max_duration_ms: int | None = None
    total_cost: float = 0.0


class ServiceManagerConfig(ServiceConfig):
    """Service manager configuration."""

    pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ServiceManagerService(BaseService):
    """Central management service for all AIFlow services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        config: ServiceManagerConfig | None = None,
    ) -> None:
        self._ext_config = config or ServiceManagerConfig()
        self._session_factory = session_factory
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "service_manager"

    @property
    def service_description(self) -> str:
        return "Central management, health, and metrics for all services"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # List services
    # ------------------------------------------------------------------

    async def list_services(self) -> list[ServiceSummary]:
        """List all known services with adapter availability."""
        from aiflow.pipeline.adapter_base import adapter_registry
        from aiflow.pipeline.adapters import discover_adapters

        discover_adapters()
        adapter_services = {k[0] for k in adapter_registry.list_adapters()}

        known = self._get_known_services()
        return [
            ServiceSummary(
                name=name,
                status="available",
                description=desc,
                has_adapter=name in adapter_services,
            )
            for name, desc in known
        ]

    # ------------------------------------------------------------------
    # Service detail
    # ------------------------------------------------------------------

    async def get_service_detail(self, name: str) -> ServiceDetail:
        """Get detailed info for a specific service."""
        from aiflow.pipeline.adapter_base import adapter_registry
        from aiflow.pipeline.adapters import discover_adapters

        discover_adapters()

        methods = [
            k[1]
            for k in adapter_registry.list_adapters()
            if k[0] == name
        ]
        has_adapter = len(methods) > 0

        # Find pipelines using this service
        pipelines: list[str] = []
        if self._session_factory:
            pipelines = await self._find_pipelines_using(name)

        desc = dict(self._get_known_services()).get(name, "")

        return ServiceDetail(
            name=name,
            status="available",
            description=desc,
            has_adapter=has_adapter,
            adapter_methods=methods,
            pipelines_using=pipelines,
        )

    # ------------------------------------------------------------------
    # Restart service
    # ------------------------------------------------------------------

    async def restart_service(self, name: str) -> bool:
        """Restart a service via the services registry.

        Returns True if restart succeeded, False otherwise.
        Note: this is a soft restart — it only works for services
        that are registered in the active ServiceRegistry.
        """
        try:
            from aiflow.api.v1.services import _get_registry

            registry = await _get_registry()
            svc = registry.get_service(name)
            if svc is None:
                return False
            await svc.stop()
            await svc.start()
            self._logger.info("service_restarted", service=name)
            return True
        except Exception as exc:
            self._logger.error("restart_failed", service=name, error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    async def get_service_metrics(
        self,
        name: str,
        period: str = "24h",
    ) -> ServiceMetrics:
        """Query aggregated metrics for a service."""
        if self._session_factory is None:
            return ServiceMetrics(service_name=name, period=period)

        from datetime import UTC, datetime

        td = self._period_to_timedelta(period)
        cutoff = datetime.now(UTC) - td

        async with self._session_factory() as session:
            r = await session.execute(
                text(
                    "SELECT "
                    "  COALESCE(SUM(call_count), 0) AS calls, "
                    "  COALESCE(SUM(success_count), 0) AS ok, "
                    "  COALESCE(SUM(error_count), 0) AS errs, "
                    "  CASE WHEN SUM(call_count) > 0 "
                    "    THEN SUM(total_duration_ms)::float "
                    "         / SUM(call_count) "
                    "    ELSE 0 END AS avg_ms, "
                    "  MIN(min_duration_ms) AS min_ms, "
                    "  MAX(max_duration_ms) AS max_ms, "
                    "  COALESCE(SUM(total_cost), 0) AS cost "
                    "FROM service_metrics "
                    "WHERE service_name = :name "
                    "  AND sampled_at >= :cutoff"
                ),
                {"name": name, "cutoff": cutoff},
            )
            row = r.fetchone()

        if row is None:
            return ServiceMetrics(service_name=name, period=period)

        calls = int(row[0])
        errs = int(row[2])
        return ServiceMetrics(
            service_name=name,
            period=period,
            call_count=calls,
            success_count=int(row[1]),
            error_count=errs,
            error_rate=round(errs / calls, 4) if calls > 0 else 0.0,
            avg_duration_ms=round(float(row[3]), 2),
            min_duration_ms=row[4],
            max_duration_ms=row[5],
            total_cost=float(row[6]),
        )

    async def record_metric(
        self,
        service_name: str,
        duration_ms: int,
        success: bool,
        cost: float = 0.0,
    ) -> None:
        """Record a single service call metric."""
        if self._session_factory is None:
            return
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text(
                        "INSERT INTO service_metrics "
                        "(service_name, call_count, success_count, "
                        " error_count, total_duration_ms, "
                        " min_duration_ms, max_duration_ms, total_cost) "
                        "VALUES (:name, 1, :ok, :err, :dur, :dur, :dur, :cost)"
                    ),
                    {
                        "name": service_name,
                        "ok": 1 if success else 0,
                        "err": 0 if success else 1,
                        "dur": duration_ms,
                        "cost": cost,
                    },
                )
                await session.commit()
        except Exception as exc:
            self._logger.warning("metric_record_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_known_services(self) -> list[tuple[str, str]]:
        """Return list of (name, description) for all known service types."""
        return [
            ("email_connector", "Multi-provider email fetching"),
            ("classifier", "Hybrid ML+LLM intent classification"),
            ("document_extractor", "PDF/DOCX extraction with Docling"),
            ("rag_engine", "RAG ingest + query with pgvector"),
            ("media_processor", "Media transcription (ffmpeg + Whisper)"),
            ("diagram_generator", "BPMN/Mermaid diagram generation"),
            ("rpa_browser", "Playwright browser automation"),
            ("human_review", "Human-in-the-loop review workflows"),
            ("notification", "Multi-channel notification sending"),
            ("data_router", "Condition-based filtering and file routing"),
            ("cache", "Redis-backed caching"),
            ("rate_limiter", "Token bucket rate limiting"),
            ("resilience", "Circuit breaker + retries"),
            ("schema_registry", "JSON schema management"),
            ("audit", "Audit logging"),
            ("health_monitor", "Health check aggregation"),
        ]

    async def _find_pipelines_using(self, service_name: str) -> list[str]:
        """Find pipeline definitions that reference this service."""
        if self._session_factory is None:
            return []
        try:
            async with self._session_factory() as session:
                r = await session.execute(
                    text(
                        "SELECT name FROM pipeline_definitions "
                        "WHERE definition::text LIKE :pattern "
                        "AND enabled = true"
                    ),
                    {"pattern": f"%{service_name}%"},
                )
                return [row[0] for row in r.fetchall()]
        except Exception:
            return []

    @staticmethod
    def _period_to_timedelta(period: str) -> timedelta:
        """Convert period shorthand to Python timedelta."""
        mapping = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        return mapping.get(period, timedelta(hours=24))
