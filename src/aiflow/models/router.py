"""Model routing - selects the best model based on cost, capability, or fallback chain.

Supports routing strategies: cost_optimized, latency_optimized, capability_match, fallback_chain.
"""
from enum import StrEnum
from typing import Any
import structlog
from aiflow.models.metadata import ModelMetadata, ModelType
from aiflow.models.registry import ModelRegistry

__all__ = ["RoutingStrategy", "ModelRouter"]

logger = structlog.get_logger(__name__)

class RoutingStrategy(StrEnum):
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    CAPABILITY_MATCH = "capability_match"
    FALLBACK_CHAIN = "fallback_chain"

class ModelRouter:
    """Routes model requests to the best available model."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def route(self, model_type: ModelType, *, strategy: RoutingStrategy = RoutingStrategy.FALLBACK_CHAIN,
              required_capability: str | None = None, preferred_model: str | None = None) -> ModelMetadata | None:
        """Select the best model based on strategy.

        Args:
            model_type: Type of model needed (llm, embedding, etc.)
            strategy: Routing strategy to use
            required_capability: Must have this capability
            preferred_model: Try this model first

        Returns:
            Selected ModelMetadata or None if no suitable model found
        """
        # Try preferred model first
        if preferred_model:
            meta = self._registry.get_or_none(preferred_model)
            if meta and meta.model_type == model_type:
                if required_capability is None or required_capability in meta.capabilities:
                    return meta

        # Get candidates
        candidates = self._registry.find_by_type(model_type)
        if required_capability:
            candidates = [m for m in candidates if required_capability in m.capabilities]

        if not candidates:
            logger.warning("no_model_found", model_type=model_type, strategy=strategy)
            return None

        if strategy == RoutingStrategy.COST_OPTIMIZED:
            return min(candidates, key=lambda m: m.cost_per_input_token + m.cost_per_output_token)
        elif strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            with_latency = [m for m in candidates if m.avg_latency_ms is not None]
            if with_latency:
                return min(with_latency, key=lambda m: m.avg_latency_ms or float('inf'))
            return candidates[0]  # fallback to priority order
        elif strategy == RoutingStrategy.CAPABILITY_MATCH:
            return candidates[0]  # already sorted by priority
        else:  # FALLBACK_CHAIN
            return candidates[0]  # sorted by priority (lowest = best)

    def get_fallback_chain(self, model_name: str, max_depth: int = 3) -> list[ModelMetadata]:
        """Get the fallback chain for a model (follows fallback_model links)."""
        chain: list[ModelMetadata] = []
        current = self._registry.get_or_none(model_name)

        for _ in range(max_depth):
            if current is None:
                break
            chain.append(current)
            if current.fallback_model:
                current = self._registry.get_or_none(current.fallback_model)
            else:
                break

        return chain

    def route_with_fallback(self, model_name: str) -> ModelMetadata | None:
        """Try the specified model, then follow its fallback chain."""
        chain = self.get_fallback_chain(model_name)
        return chain[0] if chain else None
