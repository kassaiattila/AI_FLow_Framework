"""Base service class for all AIFlow infrastructure and domain services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["ServiceStatus", "ServiceInfo", "ServiceConfig", "BaseService"]

logger = structlog.get_logger(__name__)


class ServiceStatus(str, Enum):
    """Service lifecycle status."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceInfo(BaseModel):
    """Runtime information about a service."""

    name: str
    version: str = "0.1.0"
    status: ServiceStatus = ServiceStatus.CREATED
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceConfig(BaseModel):
    """Base configuration for all services. Subclass for service-specific config."""

    enabled: bool = True


class BaseService(ABC):
    """Abstract base for all AIFlow services (infra and domain).

    Lifecycle: create -> start() -> [running] -> stop()

    Every service must implement:
    - start(): Initialize connections, warm caches, etc.
    - stop(): Clean up resources.
    - health_check(): Return True if the service is healthy.
    """

    def __init__(self, config: ServiceConfig | None = None) -> None:
        self._config = config or ServiceConfig()
        self._info = ServiceInfo(
            name=self.service_name,
            description=self.service_description,
        )
        self._logger = structlog.get_logger(f"aiflow.services.{self.service_name}")

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Unique name for this service (e.g., 'cache', 'rate_limiter')."""
        ...

    @property
    def service_description(self) -> str:
        """Human-readable description."""
        return ""

    @property
    def status(self) -> ServiceStatus:
        """Current service status."""
        return self._info.status

    @property
    def info(self) -> ServiceInfo:
        """Service runtime info."""
        return self._info

    @property
    def config(self) -> ServiceConfig:
        """Service configuration."""
        return self._config

    async def start(self) -> None:
        """Start the service. Override to add initialization logic."""
        self._info.status = ServiceStatus.STARTING
        self._logger.info("service_starting", service=self.service_name)
        try:
            await self._start()
            self._info.status = ServiceStatus.RUNNING
            self._logger.info("service_started", service=self.service_name)
        except Exception as exc:
            self._info.status = ServiceStatus.ERROR
            self._logger.error("service_start_failed", service=self.service_name, error=str(exc))
            raise

    async def stop(self) -> None:
        """Stop the service. Override to add cleanup logic."""
        self._info.status = ServiceStatus.STOPPING
        self._logger.info("service_stopping", service=self.service_name)
        try:
            await self._stop()
            self._info.status = ServiceStatus.STOPPED
            self._logger.info("service_stopped", service=self.service_name)
        except Exception as exc:
            self._info.status = ServiceStatus.ERROR
            self._logger.error("service_stop_failed", service=self.service_name, error=str(exc))
            raise

    @abstractmethod
    async def _start(self) -> None:
        """Service-specific start logic. Override in subclasses."""
        ...

    @abstractmethod
    async def _stop(self) -> None:
        """Service-specific stop logic. Override in subclasses."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the service is healthy and operational."""
        ...
