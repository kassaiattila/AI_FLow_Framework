"""In-process event bus for decoupled component communication.

Inspired by CrewAI's event system. Supports sync and async handlers.
"""
import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

__all__ = ["EventBus", "event_bus"]

logger = structlog.get_logger(__name__)

# Handler types
SyncHandler = Callable[..., None]
AsyncHandler = Callable[..., Coroutine[Any, Any, None]]
Handler = SyncHandler | AsyncHandler


class EventBus:
    """Simple pub/sub event bus for framework-internal events."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event_name: str, handler: Handler) -> None:
        """Register a handler for an event."""
        self._handlers[event_name].append(handler)
        logger.debug("event_handler_registered", event_name=event_name, handler_name=handler.__name__)

    def off(self, event_name: str, handler: Handler) -> None:
        """Unregister a handler."""
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    async def emit(self, event_name: str, **kwargs: Any) -> None:
        """Emit an event, calling all registered handlers."""
        handlers = self._handlers.get(event_name, [])
        if not handlers:
            return

        logger.debug("event_emitted", event_name=event_name, handler_count=len(handlers))

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**kwargs)
                else:
                    handler(**kwargs)
            except Exception:
                logger.exception("event_handler_error", event_name=event_name, handler=handler.__name__)

    def clear(self) -> None:
        """Remove all handlers (useful for testing)."""
        self._handlers.clear()

    @property
    def handler_count(self) -> int:
        """Total number of registered handlers."""
        return sum(len(h) for h in self._handlers.values())


# Global singleton
event_bus = EventBus()
