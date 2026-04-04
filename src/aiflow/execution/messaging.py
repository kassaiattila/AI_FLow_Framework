"""Message broker abstraction for inter-service communication."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["Message", "MessageBroker"]

logger = structlog.get_logger(__name__)


class Message(BaseModel):
    """A message in the messaging system."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageBroker:
    """In-memory message broker for development and testing."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Message], Awaitable[None]]]] = {}

    async def publish(self, message: Message) -> None:
        """Publish a message to a topic."""
        handlers = self._subscribers.get(message.topic, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as exc:
                logger.error("message_handler_error", topic=message.topic, error=str(exc))

    def subscribe(self, topic: str, handler: Callable[[Message], Awaitable[None]]) -> None:
        """Subscribe to a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[Message], Awaitable[None]]) -> None:
        """Unsubscribe from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [h for h in self._subscribers[topic] if h is not handler]
