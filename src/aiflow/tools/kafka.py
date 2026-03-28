"""Kafka adapter placeholder for AIFlow event streaming.

Note: The actual implementation requires the ``aiokafka`` dependency which
is an optional install::

    pip install aiflow[kafka]
    # or: pip install aiokafka

All public classes are usable for type-checking and testing.  The
``connect()`` methods log warnings until the real driver is wired in.

Canonical location: ``aiflow.tools.kafka``
Backward-compat re-export: ``aiflow.contrib.messaging``
"""
from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "KafkaConfig",
    "KafkaProducer",
    "KafkaConsumer",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class KafkaConfig(BaseModel):
    """Connection settings for a Kafka cluster."""

    bootstrap_servers: str = Field(
        "localhost:9092",
        description="Comma-separated list of broker addresses",
    )
    security_protocol: str = Field(
        "PLAINTEXT",
        description="Security protocol: PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL",
    )
    group_id: str = Field(
        "aiflow",
        description="Default consumer group ID",
    )


# ---------------------------------------------------------------------------
# Producer
# ---------------------------------------------------------------------------

class KafkaProducer:
    """Placeholder Kafka producer.

    Replace the placeholder bodies with real ``aiokafka.AIOKafkaProducer``
    calls once the dependency is available.
    """

    def __init__(self, config: KafkaConfig) -> None:
        self._config = config
        self._connected = False
        logger.info(
            "kafka_producer_created",
            bootstrap_servers=config.bootstrap_servers,
            security_protocol=config.security_protocol,
        )

    async def connect(self) -> None:
        """Establish connection to Kafka cluster.

        Placeholder -- logs a warning until ``aiokafka`` is wired in.
        """
        logger.warning(
            "kafka_producer_connect_placeholder",
            msg="aiokafka not installed; using no-op producer",
            bootstrap_servers=self._config.bootstrap_servers,
        )
        self._connected = True

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to the given *topic*.

        Placeholder -- serialises to JSON and logs the payload.
        """
        if not self._connected:
            logger.error("kafka_producer_not_connected")
            raise RuntimeError("KafkaProducer is not connected. Call connect() first.")

        logger.info(
            "kafka_publish_placeholder",
            topic=topic,
            message_keys=list(message.keys()) if isinstance(message, dict) else None,
        )

    async def close(self) -> None:
        """Gracefully close the producer connection."""
        self._connected = False
        logger.info("kafka_producer_closed")

    @property
    def is_connected(self) -> bool:
        return self._connected


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------

class KafkaConsumer:
    """Placeholder Kafka consumer.

    Replace the placeholder bodies with real ``aiokafka.AIOKafkaConsumer``
    calls once the dependency is available.
    """

    def __init__(self, config: KafkaConfig) -> None:
        self._config = config
        self._connected = False
        self._subscriptions: list[str] = []
        logger.info(
            "kafka_consumer_created",
            bootstrap_servers=config.bootstrap_servers,
            group_id=config.group_id,
        )

    async def connect(self) -> None:
        """Establish connection to Kafka cluster.

        Placeholder -- logs a warning until ``aiokafka`` is wired in.
        """
        logger.warning(
            "kafka_consumer_connect_placeholder",
            msg="aiokafka not installed; using no-op consumer",
            bootstrap_servers=self._config.bootstrap_servers,
        )
        self._connected = True

    async def subscribe(self, topic: str, group_id: str | None = None) -> None:
        """Subscribe to a *topic*.

        Placeholder -- records the subscription locally.
        """
        effective_group = group_id or self._config.group_id
        self._subscriptions.append(topic)
        logger.info(
            "kafka_subscribe_placeholder",
            topic=topic,
            group_id=effective_group,
        )

    async def poll(self, timeout_ms: int = 1000) -> list[dict[str, Any]]:
        """Poll for new messages.

        Placeholder -- always returns an empty list.
        """
        if not self._connected:
            logger.error("kafka_consumer_not_connected")
            raise RuntimeError("KafkaConsumer is not connected. Call connect() first.")

        logger.debug(
            "kafka_poll_placeholder",
            subscriptions=self._subscriptions,
            timeout_ms=timeout_ms,
        )
        return []

    async def close(self) -> None:
        """Gracefully close the consumer connection."""
        self._connected = False
        self._subscriptions.clear()
        logger.info("kafka_consumer_closed")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscriptions(self) -> list[str]:
        return list(self._subscriptions)
