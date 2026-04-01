"""Schema registry service — centralized versioned JSON schema management."""

from aiflow.services.schema_registry.service import (
    SchemaRegistryConfig,
    SchemaRegistryService,
)

__all__ = ["SchemaRegistryConfig", "SchemaRegistryService"]
