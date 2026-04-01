"""Service registry for managing AIFlow infrastructure and domain services."""
from __future__ import annotations

from typing import Any

import structlog

from aiflow.services.base import BaseService, ServiceInfo, ServiceStatus

__all__ = ["ServiceRegistry"]

logger = structlog.get_logger(__name__)


class ServiceRegistry:
    """Central registry for all AIFlow services.

    Manages service lifecycle (start/stop) and provides discovery.
    Singleton-like usage: one registry per application instance.
    """

    def __init__(self) -> None:
        self._services: dict[str, BaseService] = {}

    def register(self, service: BaseService) -> None:
        """Register a service. Raises ValueError if name already taken."""
        name = service.service_name
        if name in self._services:
            raise ValueError(
                f"Service '{name}' already registered. "
                f"Registered: {list(self._services.keys())}"
            )
        self._services[name] = service
        logger.info("service_registered", service=name)

    def get(self, name: str) -> BaseService:
        """Get a service by name. Raises KeyError if not found."""
        if name not in self._services:
            raise KeyError(
                f"Service '{name}' not found. "
                f"Available: {list(self._services.keys())}"
            )
        return self._services[name]

    def get_or_none(self, name: str) -> BaseService | None:
        """Get a service by name, or None if not found."""
        return self._services.get(name)

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def unregister(self, name: str) -> None:
        """Unregister a service. Raises KeyError if not found."""
        if name not in self._services:
            raise KeyError(f"Service '{name}' not found")
        del self._services[name]
        logger.info("service_unregistered", service=name)

    def list_services(self) -> list[ServiceInfo]:
        """Return info for all registered services."""
        return [svc.info for svc in self._services.values()]

    def list_names(self) -> list[str]:
        """Return all registered service names."""
        return list(self._services.keys())

    async def start_all(self) -> dict[str, bool]:
        """Start all registered services. Returns {name: success}."""
        results: dict[str, bool] = {}
        for name, service in self._services.items():
            try:
                await service.start()
                results[name] = True
            except Exception as exc:
                logger.error("service_start_failed", service=name, error=str(exc))
                results[name] = False
        return results

    async def stop_all(self) -> dict[str, bool]:
        """Stop all registered services in reverse order. Returns {name: success}."""
        results: dict[str, bool] = {}
        for name in reversed(list(self._services.keys())):
            service = self._services[name]
            try:
                await service.stop()
                results[name] = True
            except Exception as exc:
                logger.error("service_stop_failed", service=name, error=str(exc))
                results[name] = False
        return results

    async def health_check_all(self) -> dict[str, Any]:
        """Run health checks on all services. Returns {name: {status, healthy}}."""
        results: dict[str, Any] = {}
        for name, service in self._services.items():
            try:
                healthy = await service.health_check()
                results[name] = {
                    "status": service.status.value,
                    "healthy": healthy,
                }
            except Exception as exc:
                results[name] = {
                    "status": ServiceStatus.ERROR.value,
                    "healthy": False,
                    "error": str(exc),
                }
        return results

    def __len__(self) -> int:
        return len(self._services)

    def __contains__(self, name: str) -> bool:
        return name in self._services

    def __repr__(self) -> str:
        return f"ServiceRegistry(services={list(self._services.keys())})"
