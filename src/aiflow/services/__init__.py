"""AIFlow services layer — infrastructure and domain services.

Infrastructure (F0): cache, config versioning, rate limiter, resilience, schema registry.
Domain (F1-F4): document extractor, email connector, classifier, RAG engine, RPA, media, diagram.
"""

from aiflow.services.base import (
    BaseService,
    ServiceConfig,
    ServiceInfo,
    ServiceStatus,
)
from aiflow.services.cache import CacheConfig, CacheService
from aiflow.services.classifier import (
    ClassificationResult,
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
)
from aiflow.services.config import (
    ConfigVersion,
    ConfigVersioningConfig,
    ConfigVersioningService,
)
from aiflow.services.email_connector import (
    ConnectorProvider,
    EmailConnectorConfig,
    EmailConnectorService,
    FetchedEmail,
    FetchResult,
)
from aiflow.services.rag_engine import (
    RAGEngineConfig,
    RAGEngineService,
)
from aiflow.services.rate_limiter import (
    RateLimiterConfig,
    RateLimiterService,
    RateLimitRule,
)
from aiflow.services.registry import ServiceRegistry
from aiflow.services.resilience import (
    CircuitState,
    ResilienceConfig,
    ResilienceRule,
    ResilienceService,
)
from aiflow.services.schema_registry import (
    SchemaRegistryConfig,
    SchemaRegistryService,
)

__all__ = [
    # Base
    "BaseService",
    "ServiceConfig",
    "ServiceInfo",
    "ServiceRegistry",
    "ServiceStatus",
    # Cache
    "CacheConfig",
    "CacheService",
    # Classifier
    "ClassificationResult",
    "ClassificationStrategy",
    "ClassifierConfig",
    "ClassifierService",
    # Config Versioning
    "ConfigVersion",
    "ConfigVersioningConfig",
    "ConfigVersioningService",
    # Email Connector
    "ConnectorProvider",
    "EmailConnectorConfig",
    "EmailConnectorService",
    "FetchedEmail",
    "FetchResult",
    # RAG Engine
    "RAGEngineConfig",
    "RAGEngineService",
    # Rate Limiter
    "RateLimiterConfig",
    "RateLimiterService",
    "RateLimitRule",
    # Resilience
    "CircuitState",
    "ResilienceConfig",
    "ResilienceRule",
    "ResilienceService",
    # Schema Registry
    "SchemaRegistryConfig",
    "SchemaRegistryService",
]
