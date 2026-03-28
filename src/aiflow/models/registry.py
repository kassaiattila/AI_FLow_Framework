"""In-memory model registry for tracking available models."""
import structlog
from aiflow.core.registry import Registry
from aiflow.models.metadata import ModelMetadata, ModelType

__all__ = ["ModelRegistry"]

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """Registry for available ML/LLM models with lookup by type and capability."""

    def __init__(self) -> None:
        self._registry: Registry[ModelMetadata] = Registry(name="models")

    def register(self, metadata: ModelMetadata) -> None:
        """Register a model."""
        self._registry.register(metadata.name, metadata)

    def get(self, name: str) -> ModelMetadata:
        """Get model metadata by name."""
        return self._registry.get(name)

    def get_or_none(self, name: str) -> ModelMetadata | None:
        """Get model metadata or None."""
        return self._registry.get_or_none(name)

    def find_by_type(self, model_type: ModelType) -> list[ModelMetadata]:
        """Find all models of a given type, sorted by priority."""
        results = [
            meta for _, meta in self._registry.list_items()
            if meta.model_type == model_type
        ]
        return sorted(results, key=lambda m: m.priority)

    def find_by_capability(self, capability: str) -> list[ModelMetadata]:
        """Find models with a specific capability."""
        return [
            meta for _, meta in self._registry.list_items()
            if capability in meta.capabilities
        ]

    def get_fallback(self, name: str) -> ModelMetadata | None:
        """Get the fallback model for a given model."""
        meta = self.get_or_none(name)
        if meta and meta.fallback_model:
            return self.get_or_none(meta.fallback_model)
        return None

    def list_all(self) -> list[ModelMetadata]:
        """List all registered models."""
        return [meta for _, meta in self._registry.list_items()]

    def __len__(self) -> int:
        return len(self._registry)
