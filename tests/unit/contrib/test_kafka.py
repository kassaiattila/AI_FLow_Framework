"""
@test_registry:
    suite: core-unit
    component: contrib.messaging.kafka
    covers: [src/aiflow/contrib/messaging/kafka.py]
    phase: 7
    priority: medium
    estimated_duration_ms: 100
    requires_services: []
    tags: [contrib, messaging, kafka, integration-point]
"""

from aiflow.contrib.messaging.kafka import KafkaConfig, KafkaConsumer, KafkaProducer


class TestKafkaConfig:
    def test_default_config(self):
        config = KafkaConfig()
        assert config.bootstrap_servers == "localhost:9092"
        assert config.security_protocol == "PLAINTEXT"
        assert config.group_id == "aiflow"

    def test_custom_config(self):
        config = KafkaConfig(
            bootstrap_servers="broker1:9092,broker2:9092",
            security_protocol="SSL",
            group_id="my-group",
        )
        assert config.bootstrap_servers == "broker1:9092,broker2:9092"
        assert config.security_protocol == "SSL"
        assert config.group_id == "my-group"


class TestKafkaProducer:
    def test_create_producer(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        producer = KafkaProducer(config=config)
        assert producer._config == config
        assert producer.is_connected is False

    def test_publish_method_exists(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        producer = KafkaProducer(config=config)
        assert hasattr(producer, "publish")
        assert callable(producer.publish)

    def test_connect_method_exists(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        producer = KafkaProducer(config=config)
        assert hasattr(producer, "connect")
        assert callable(producer.connect)


class TestKafkaConsumer:
    def test_create_consumer(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        consumer = KafkaConsumer(config=config)
        assert consumer._config == config
        assert consumer.is_connected is False

    def test_subscribe_method_exists(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        consumer = KafkaConsumer(config=config)
        assert hasattr(consumer, "subscribe")
        assert callable(consumer.subscribe)

    def test_poll_method_exists(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        consumer = KafkaConsumer(config=config)
        assert hasattr(consumer, "poll")
        assert callable(consumer.poll)

    def test_initial_subscriptions_empty(self):
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        consumer = KafkaConsumer(config=config)
        assert consumer.subscriptions == []
