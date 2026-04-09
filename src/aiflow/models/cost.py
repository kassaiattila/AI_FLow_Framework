"""Model cost calculation and tracking."""

import structlog

__all__ = ["ModelCostCalculator"]

logger = structlog.get_logger(__name__)

# Known model pricing (per 1M tokens, USD) - updated periodically
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4.1": {"input": 2.00, "output": 8.00},
    "openai/gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "anthropic/claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "anthropic/claude-haiku-4-20250514": {"input": 0.80, "output": 4.00},
    "openai/text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "openai/text-embedding-3-large": {"input": 0.13, "output": 0.0},
}


class ModelCostCalculator:
    """Calculate costs for model calls based on token usage."""

    def __init__(self, custom_pricing: dict[str, dict[str, float]] | None = None) -> None:
        self._pricing = {**DEFAULT_PRICING}
        if custom_pricing:
            self._pricing.update(custom_pricing)

    def calculate(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for a model call."""
        pricing = self._pricing.get(model)
        if pricing is None:
            logger.debug("model_pricing_unknown", model=model)
            return 0.0
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
        return round(input_cost + output_cost, 8)

    def estimate_cost(
        self, model: str, estimated_input_tokens: int, estimated_output_tokens: int
    ) -> float:
        """Estimate cost before making a call (for budget checking)."""
        return self.calculate(model, estimated_input_tokens, estimated_output_tokens)

    def get_pricing(self, model: str) -> dict[str, float] | None:
        """Get pricing info for a model."""
        return self._pricing.get(model)

    def register_pricing(
        self, model: str, input_per_million: float, output_per_million: float
    ) -> None:
        """Register or update pricing for a model."""
        self._pricing[model] = {"input": input_per_million, "output": output_per_million}

    def list_priced_models(self) -> list[str]:
        """List all models with known pricing."""
        return list(self._pricing.keys())
