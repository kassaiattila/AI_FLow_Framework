"""Projected USD cost estimator for pre-flight cost guardrails — Sprint N / S122.

Wraps ``litellm.cost_per_token`` when the model is in the pricing table; falls
back to a per-tier ceiling when it is not. The estimator is intentionally
stateless so it can be constructed per-request without shared state.
"""

from __future__ import annotations

from typing import Literal

import structlog

__all__ = [
    "CostEstimator",
    "ModelTier",
    "PER_TIER_FALLBACK_USD_PER_1K_IN",
    "PER_TIER_FALLBACK_USD_PER_1K_OUT",
]

logger = structlog.get_logger(__name__)

ModelTier = Literal["premium", "standard", "cheap"]

PER_TIER_FALLBACK_USD_PER_1K_IN: dict[ModelTier, float] = {
    "premium": 0.03,
    "standard": 0.01,
    "cheap": 0.001,
}
PER_TIER_FALLBACK_USD_PER_1K_OUT: dict[ModelTier, float] = {
    "premium": 0.06,
    "standard": 0.02,
    "cheap": 0.002,
}

_CHEAP_KEYWORDS = ("mini", "haiku", "flash", "nano", "small")
_PREMIUM_KEYWORDS = ("gpt-4", "o1", "opus", "sonnet-4", "claude-3-opus")


def _tier_for_model(model: str) -> ModelTier:
    low = model.lower()
    if any(k in low for k in _CHEAP_KEYWORDS):
        return "cheap"
    if any(k in low for k in _PREMIUM_KEYWORDS):
        return "premium"
    return "standard"


class CostEstimator:
    """Projected USD cost for an LLM call."""

    def estimate(self, model: str, input_tokens: int, max_output_tokens: int) -> float:
        input_tokens = max(int(input_tokens), 0)
        max_output_tokens = max(int(max_output_tokens), 0)

        try:
            import litellm

            prompt_cost, completion_cost = litellm.cost_per_token(
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=max_output_tokens,
            )
            total = float(prompt_cost) + float(completion_cost)
            logger.debug(
                "cost_estimated",
                model=model,
                input_tokens=input_tokens,
                max_output_tokens=max_output_tokens,
                projected_usd=round(total, 6),
                provider_pricing_used=True,
            )
            return total
        except Exception as exc:
            logger.info(
                "cost_estimator_fallback",
                model=model,
                reason=str(exc)[:200],
                provider_pricing_used=False,
            )

        tier = _tier_for_model(model)
        in_rate = PER_TIER_FALLBACK_USD_PER_1K_IN[tier]
        out_rate = PER_TIER_FALLBACK_USD_PER_1K_OUT[tier]
        total = (input_tokens / 1000.0) * in_rate + (max_output_tokens / 1000.0) * out_rate
        logger.info(
            "cost_estimated",
            model=model,
            input_tokens=input_tokens,
            max_output_tokens=max_output_tokens,
            projected_usd=round(total, 6),
            provider_pricing_used=False,
            tier=tier,
        )
        return total
