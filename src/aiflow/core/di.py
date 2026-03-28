"""Lightweight dependency injection container for framework services.

Services are registered by type and retrieved by type. Supports lazy initialization.

DEPRECATED: Skills use SkillRunner.from_env() instead. Planned for Phase B review.
"""
from typing import Any, TypeVar, Callable

import structlog

__all__ = ["Container"]

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Container:
    """Simple DI container for AIFlow services.

    Usage:
        container = Container()
        container.register(DatabasePool, my_pool)
        pool = container.resolve(DatabasePool)

        # Or with factory (lazy):
        container.register_factory(DatabasePool, create_pool)
        pool = container.resolve(DatabasePool)  # calls create_pool() on first access
    """

    def __init__(self) -> None:
        self._instances: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}

    def register(self, service_type: type[T], instance: T) -> None:
        """Register a service instance."""
        self._instances[service_type] = instance
        logger.debug("di_service_registered", service=service_type.__name__)

    def register_factory(self, service_type: type[T], factory: Callable[[], T]) -> None:
        """Register a lazy factory for a service."""
        self._factories[service_type] = factory
        logger.debug("di_factory_registered", service=service_type.__name__)

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service by type. Creates from factory on first access if needed."""
        # Direct instance?
        if service_type in self._instances:
            return self._instances[service_type]

        # Factory?
        if service_type in self._factories:
            instance = self._factories[service_type]()
            self._instances[service_type] = instance
            del self._factories[service_type]
            logger.debug("di_service_created_from_factory", service=service_type.__name__)
            return instance

        raise KeyError(
            f"Service {service_type.__name__} not registered. "
            f"Available: {[t.__name__ for t in self._instances | self._factories]}"
        )

    def has(self, service_type: type) -> bool:
        """Check if a service is registered (instance or factory)."""
        return service_type in self._instances or service_type in self._factories

    def clear(self) -> None:
        """Remove all services (useful for testing)."""
        self._instances.clear()
        self._factories.clear()

    def __repr__(self) -> str:
        instances = [t.__name__ for t in self._instances]
        factories = [t.__name__ for t in self._factories]
        return f"Container(instances={instances}, factories={factories})"
