"""Projected USD cost estimator for pre-flight cost guardrails — Sprint N / S122.

Wraps ``litellm.cost_per_token`` when the model is in the pricing table; falls
back to a per-tier ceiling when it is not. The estimator is intentionally
stateless so it can be constructed per-request without shared state.

Sprint U / S154 (SN-FU-2): the per-tier fallback rates are now operator-tunable
via :class:`aiflow.core.config.CostGuardrailSettings.tier_fallback_in_per_1k`
and ``tier_fallback_out_per_1k``. Default values match the Sprint N hard-codes.
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

# Default fallback ceilings (USD per 1k tokens) used when ``litellm.cost_per_token``
# returns no match. Sprint U / S154 made these env-tunable via
# CostGuardrailSettings.tier_fallback_{in,out}_per_1k; these dicts remain as the
# default values that those settings fields default to.
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
    """Projected USD cost for an LLM call.

    Sprint U / S154: ``tier_fallback_in_per_1k`` and ``tier_fallback_out_per_1k``
    constructor args let callers override the per-tier fallback ceilings without
    touching module-level constants. When ``None`` the estimator reads the
    settings (or the module defaults if settings unavailable). Tests can pass
    explicit dicts for hermetic control.
    """

    def __init__(
        self,
        tier_fallback_in_per_1k: dict[str, float] | None = None,
        tier_fallback_out_per_1k: dict[str, float] | None = None,
    ) -> None:
        self._in_rates = self._resolve_rates(
            tier_fallback_in_per_1k, "in", PER_TIER_FALLBACK_USD_PER_1K_IN
        )
        self._out_rates = self._resolve_rates(
            tier_fallback_out_per_1k, "out", PER_TIER_FALLBACK_USD_PER_1K_OUT
        )

    @staticmethod
    def _resolve_rates(
        explicit: dict[str, float] | None,
        direction: str,
        module_default: dict[ModelTier, float],
    ) -> dict[ModelTier, float]:
        if explicit is not None:
            return {tier: float(rate) for tier, rate in explicit.items()}  # type: ignore[misc]
        try:
            from aiflow.core.config import get_settings

            settings = get_settings().cost_guardrail
            field = (
                settings.tier_fallback_in_per_1k
                if direction == "in"
                else settings.tier_fallback_out_per_1k
            )
            return {tier: float(rate) for tier, rate in field.items()}  # type: ignore[misc]
        except Exception:
            # Settings unavailable (e.g. during early import) — fall back to module defaults.
            return dict(module_default)

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
        in_rate = self._in_rates.get(tier, PER_TIER_FALLBACK_USD_PER_1K_IN[tier])
        out_rate = self._out_rates.get(tier, PER_TIER_FALLBACK_USD_PER_1K_OUT[tier])
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
