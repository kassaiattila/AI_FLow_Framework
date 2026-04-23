"""Pre-flight cost guardrail — Sprint N / S122.

Refuses an LLM or pipeline call whose projected cost exceeds the tenant's
remaining budget, *before* any cost is incurred. Gated behind a feature flag
(``AIFLOW_COST_GUARDRAIL__ENABLED``) and a dry-run mode
(``AIFLOW_COST_GUARDRAIL__DRY_RUN``) so rollout is safe: flag-off is a no-op,
flag-on with dry-run logs over-budget events but still allows the call, and
only when dry-run is turned off does the guardrail refuse.

The module returns a :class:`PreflightDecision`; it is the caller's job to
raise :class:`aiflow.core.errors.CostGuardrailRefused` on ``allowed=False``.
That keeps this module pure and test-friendly while letting each wiring site
shape its own retry / logging semantics.
"""

from __future__ import annotations

from typing import Literal

import structlog
from pydantic import BaseModel

from aiflow.guardrails.cost_estimator import CostEstimator
from aiflow.services.tenant_budgets import BudgetPeriod, TenantBudgetService

__all__ = [
    "CostPreflightGuardrail",
    "PreflightDecision",
    "PreflightReason",
    "build_guardrail_from_settings",
]

logger = structlog.get_logger(__name__)

PreflightReason = Literal[
    "disabled",
    "no_budget",
    "under_budget",
    "over_budget",
    "dry_run_over_budget",
]


class PreflightDecision(BaseModel):
    """Outcome of a pre-flight cost check."""

    allowed: bool
    projected_usd: float
    remaining_usd: float | None
    reason: PreflightReason
    period: BudgetPeriod
    dry_run: bool


class CostPreflightGuardrail:
    """Stateless pre-flight cost check.

    Constructor deps are injected so tests can pass fakes:
    * ``budgets`` — :class:`TenantBudgetService` for ``get_remaining``.
    * ``estimator`` — :class:`CostEstimator` (default constructed if ``None``).
    * ``enabled`` / ``dry_run`` / ``period`` — feature-flag knobs (also read
      from :class:`aiflow.core.config.CostGuardrailSettings`).
    """

    def __init__(
        self,
        budgets: TenantBudgetService,
        estimator: CostEstimator | None = None,
        *,
        enabled: bool = False,
        dry_run: bool = True,
        period: BudgetPeriod = "daily",
    ) -> None:
        self._budgets = budgets
        self._estimator = estimator or CostEstimator()
        self._enabled = enabled
        self._dry_run = dry_run
        self._period = period

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    @property
    def period(self) -> BudgetPeriod:
        return self._period

    async def check(
        self,
        tenant_id: str,
        *,
        model: str,
        input_tokens: int,
        max_output_tokens: int,
    ) -> PreflightDecision:
        if not self._enabled:
            return PreflightDecision(
                allowed=True,
                projected_usd=0.0,
                remaining_usd=None,
                reason="disabled",
                period=self._period,
                dry_run=self._dry_run,
            )

        projected = self._estimator.estimate(
            model=model,
            input_tokens=input_tokens,
            max_output_tokens=max_output_tokens,
        )

        view = await self._budgets.get_remaining(tenant_id, self._period)
        if view is None:
            logger.debug(
                "cost_preflight_no_budget",
                tenant_id=tenant_id,
                period=self._period,
                projected_usd=round(projected, 6),
            )
            return PreflightDecision(
                allowed=True,
                projected_usd=projected,
                remaining_usd=None,
                reason="no_budget",
                period=self._period,
                dry_run=self._dry_run,
            )

        remaining = view.remaining_usd
        if projected <= remaining:
            logger.debug(
                "cost_preflight_under_budget",
                tenant_id=tenant_id,
                period=self._period,
                projected_usd=round(projected, 6),
                remaining_usd=round(remaining, 6),
            )
            return PreflightDecision(
                allowed=True,
                projected_usd=projected,
                remaining_usd=remaining,
                reason="under_budget",
                period=self._period,
                dry_run=self._dry_run,
            )

        if self._dry_run:
            logger.warning(
                "cost_preflight_over_budget_dry_run",
                tenant_id=tenant_id,
                period=self._period,
                projected_usd=round(projected, 6),
                remaining_usd=round(remaining, 6),
                model=model,
            )
            return PreflightDecision(
                allowed=True,
                projected_usd=projected,
                remaining_usd=remaining,
                reason="dry_run_over_budget",
                period=self._period,
                dry_run=True,
            )

        logger.warning(
            "cost_preflight_refused",
            tenant_id=tenant_id,
            period=self._period,
            projected_usd=round(projected, 6),
            remaining_usd=round(remaining, 6),
            model=model,
        )
        return PreflightDecision(
            allowed=False,
            projected_usd=projected,
            remaining_usd=remaining,
            reason="over_budget",
            period=self._period,
            dry_run=False,
        )


async def build_guardrail_from_settings() -> CostPreflightGuardrail | None:
    """Construct a guardrail from ``get_settings().cost_guardrail`` and the shared pool.

    Returns ``None`` when the guardrail is disabled OR the DB pool cannot be
    acquired — callers treat ``None`` as a silent skip. The shared asyncpg
    pool is resolved lazily via :func:`aiflow.api.deps.get_pool` so Sprint N's
    guardrail adds zero import-time coupling to existing surfaces.
    """
    from aiflow.core.config import get_settings

    settings = get_settings().cost_guardrail
    if not settings.enabled:
        return None

    try:
        from aiflow.api.deps import get_pool

        pool = await get_pool()
    except Exception as exc:  # pragma: no cover — defensive only
        logger.debug("cost_preflight_pool_unavailable", error=str(exc)[:200])
        return None

    return CostPreflightGuardrail(
        budgets=TenantBudgetService(pool=pool),
        enabled=settings.enabled,
        dry_run=settings.dry_run,
        period=settings.period,
    )
