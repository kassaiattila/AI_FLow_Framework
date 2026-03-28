"""Messaging integrations (Kafka, RabbitMQ, etc.).

Backward-compat re-export. Canonical location: ``aiflow.tools.kafka``
"""
from aiflow.tools.kafka import KafkaConfig, KafkaProducer, KafkaConsumer

__all__ = ["KafkaConfig", "KafkaProducer", "KafkaConsumer"]
