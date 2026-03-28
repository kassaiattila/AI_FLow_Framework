"""Universal registry for framework components (workflows, skills, agents).

Thread-safe, supports registration, lookup, and listing.
"""
from typing import Any, TypeVar, Generic

import structlog

__all__ = ["Registry"]

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry for named components."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._items: dict[str, T] = {}

    def register(self, key: str, item: T) -> None:
        """Register an item. Raises ValueError if key already exists."""
        if key in self._items:
            raise ValueError(f"{self._name} registry: '{key}' already registered")
        self._items[key] = item
        logger.info("registry_item_registered", registry=self._name, key=key)

    def get(self, key: str) -> T:
        """Get an item by key. Raises KeyError if not found."""
        if key not in self._items:
            raise KeyError(f"{self._name} registry: '{key}' not found. Available: {list(self._items.keys())}")
        return self._items[key]

    def get_or_none(self, key: str) -> T | None:
        """Get an item by key, or None if not found."""
        return self._items.get(key)

    def has(self, key: str) -> bool:
        """Check if a key is registered."""
        return key in self._items

    def unregister(self, key: str) -> None:
        """Remove an item. Raises KeyError if not found."""
        if key not in self._items:
            raise KeyError(f"{self._name} registry: '{key}' not found")
        del self._items[key]
        logger.info("registry_item_unregistered", registry=self._name, key=key)

    def list_keys(self) -> list[str]:
        """Return all registered keys."""
        return list(self._items.keys())

    def list_items(self) -> list[tuple[str, T]]:
        """Return all (key, item) pairs."""
        return list(self._items.items())

    def clear(self) -> None:
        """Remove all items (useful for testing)."""
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, key: str) -> bool:
        return key in self._items

    def __repr__(self) -> str:
        return f"Registry(name={self._name!r}, items={len(self._items)})"
