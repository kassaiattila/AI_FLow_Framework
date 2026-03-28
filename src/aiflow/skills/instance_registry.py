"""Instance registry - in-memory registry for active skill instances.

Wraps the core Registry and provides instance-specific queries
(by customer, by skill template, by status).
"""
from __future__ import annotations

import structlog

from aiflow.core.registry import Registry
from aiflow.skills.instance import InstanceConfig

__all__ = ["InstanceRegistry"]

logger = structlog.get_logger(__name__)


class InstanceRegistry:
    """In-memory registry for loaded InstanceConfig objects.

    Provides lookups by instance_name, customer, and skill_template.
    """

    def __init__(self) -> None:
        self._registry: Registry[InstanceConfig] = Registry(name="instances")

    def register(self, config: InstanceConfig) -> None:
        """Register an instance config.

        Args:
            config: Validated InstanceConfig.

        Raises:
            ValueError: If instance_name is already registered.
        """
        self._registry.register(config.instance_name, config)
        logger.info(
            "instance_registered",
            instance_name=config.instance_name,
            customer=config.customer,
            skill_template=config.skill_template,
        )

    def get(self, instance_name: str) -> InstanceConfig:
        """Get an instance config by name.

        Raises:
            KeyError: If not found.
        """
        return self._registry.get(instance_name)

    def get_or_none(self, instance_name: str) -> InstanceConfig | None:
        """Get an instance config by name, or None."""
        return self._registry.get_or_none(instance_name)

    def has(self, instance_name: str) -> bool:
        """Check if an instance is registered."""
        return self._registry.has(instance_name)

    def unregister(self, instance_name: str) -> None:
        """Remove an instance.

        Raises:
            KeyError: If not found.
        """
        self._registry.unregister(instance_name)

    def list_all(self) -> list[InstanceConfig]:
        """Return all registered instance configs."""
        return [config for _, config in self._registry.list_items()]

    def list_by_customer(self, customer: str) -> list[InstanceConfig]:
        """Return all instances for a given customer."""
        return [
            config for _, config in self._registry.list_items()
            if config.customer == customer
        ]

    def list_by_skill(self, skill_template: str) -> list[InstanceConfig]:
        """Return all instances of a given skill template."""
        return [
            config for _, config in self._registry.list_items()
            if config.skill_template == skill_template
        ]

    def list_enabled(self) -> list[InstanceConfig]:
        """Return only enabled instances."""
        return [
            config for _, config in self._registry.list_items()
            if config.enabled
        ]

    def list_names(self) -> list[str]:
        """Return all registered instance names."""
        return self._registry.list_keys()

    def clear(self) -> None:
        """Remove all instances (for testing)."""
        self._registry.clear()

    def __len__(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        return f"InstanceRegistry(count={len(self)})"
