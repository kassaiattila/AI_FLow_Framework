"""
@test_registry:
    suite: integration-guardrails
    component: guardrails.cost_preflight
    covers:
        - src/aiflow/guardrails/cost_preflight.py
        - src/aiflow/guardrails/cost_estimator.py
        - src/aiflow/services/tenant_budgets/service.py
    phase: v1.4.10
    priority: critical
    estimated_duration_ms: 1500
    requires_services: [postgres]
    tags: [integration, guardrails, cost_preflight, tenant_budgets, sprint_n, s122, postgres]

Exercises the Sprint N / S122 pre-flight guardrail end-to-end against real
Docker PostgreSQL (port 5433). Seeds a ``tenant_budgets`` row, inserts a
partial ``cost_records`` row, and asserts:

1. Under-budget projection → allowed=True, reason=under_budget.
2. Over-budget projection (enforced) → allowed=False, reason=over_budget,
   AND :class:`CostGuardrailRefused` carries the structured 429 payload when
   raised by the wiring layer.
3. Over-budget projection (DRY_RUN) → allowed=True, reason=dry_run_over_budget,
   i.e. enforcement is gated by the flag.

SOHA NE mock — real asyncpg pool against Docker PostgreSQL.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import asyncpg
import pytest
import pytest_asyncio

from aiflow.core.errors import CostGuardrailRefused
from aiflow.guardrails.cost_estimator import CostEstimator
from aiflow.guardrails.cost_preflight import CostPreflightGuardrail
from aiflow.services.tenant_budgets import TenantBudgetService

pytestmark = pytest.mark.integration


def _resolve_db_url() -> str:
    raw = os.getenv(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return raw.replace("postgresql+asyncpg://", "postgresql://")


@pytest_asyncio.fixture
async def seeded_tenant():
    """Fresh pool + seeded tenant_budgets + cost_records rows for one test."""
    url = _resolve_db_url()
    try:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    tenant_id = f"s122-preflight-{uuid.uuid4().hex[:8]}"
    budget_limit = 0.01  # daily limit in USD
    used_cost = 0.009  # already spent

    async with pool.acquire() as conn:
        # Guard against missing migrations — skip if tenant_budgets is absent.
        row = await conn.fetchrow(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'tenant_budgets'
            """
        )
        if row is None:
            await pool.close()
            pytest.skip("tenant_budgets table missing — run `alembic upgrade head`.")

        await conn.execute(
            """
            INSERT INTO tenant_budgets
                (tenant_id, period, limit_usd, alert_threshold_pct, enabled, updated_at)
            VALUES ($1, 'daily', $2, ARRAY[50, 80, 95]::integer[], true, NOW())
            """,
            tenant_id,
            budget_limit,
        )
        await conn.execute(
            """
            INSERT INTO cost_records
                (id, step_name, model, provider, input_tokens, output_tokens,
                 cost_usd, tenant_id, recorded_at)
            VALUES ($1, 's122-seed', 'test-model', 'test', 100, 10, $2, $3, $4)
            """,
            uuid.uuid4(),
            used_cost,
            tenant_id,
            datetime.now(UTC),
        )

    yield pool, tenant_id, budget_limit, used_cost

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM cost_records WHERE tenant_id = $1", tenant_id)
        await conn.execute("DELETE FROM tenant_budgets WHERE tenant_id = $1", tenant_id)
    await pool.close()


class _FixedEstimator(CostEstimator):
    """Deterministic estimator for reproducible pre-flight math."""

    def __init__(self, projected_usd: float) -> None:
        self._projected = projected_usd

    def estimate(self, model: str, input_tokens: int, max_output_tokens: int) -> float:
        return self._projected


class TestCostPreflightGuardrailIntegration:
    @pytest.mark.asyncio
    async def test_under_budget_allows_call(self, seeded_tenant):
        pool, tenant_id, _, _ = seeded_tenant
        svc = TenantBudgetService(pool=pool)
        guardrail = CostPreflightGuardrail(
            budgets=svc,
            estimator=_FixedEstimator(0.0005),  # remaining ~ 0.001 → under
            enabled=True,
            dry_run=False,
        )
        decision = await guardrail.check(
            tenant_id,
            model="gpt-4o-mini",
            input_tokens=500,
            max_output_tokens=50,
        )
        assert decision.allowed is True
        assert decision.reason == "under_budget"
        assert decision.remaining_usd is not None
        # remaining ≈ limit (0.01) - used (0.009) ≈ 0.001
        assert decision.remaining_usd == pytest.approx(0.001, abs=1e-6)

    @pytest.mark.asyncio
    async def test_over_budget_enforced_refuses_with_structured_payload(self, seeded_tenant):
        pool, tenant_id, _, _ = seeded_tenant
        svc = TenantBudgetService(pool=pool)
        guardrail = CostPreflightGuardrail(
            budgets=svc,
            estimator=_FixedEstimator(0.02),  # remaining ~ 0.001 → over
            enabled=True,
            dry_run=False,
        )
        decision = await guardrail.check(
            tenant_id,
            model="gpt-4o",
            input_tokens=10000,
            max_output_tokens=2000,
        )
        assert decision.allowed is False
        assert decision.reason == "over_budget"
        assert decision.dry_run is False

        # Wiring layer converts the refusal into a structured 429 payload.
        err = CostGuardrailRefused(
            tenant_id=tenant_id,
            projected_usd=decision.projected_usd,
            remaining_usd=decision.remaining_usd or 0.0,
            period=decision.period,
            reason=decision.reason,
            dry_run=decision.dry_run,
        )
        assert err.http_status == 429
        assert err.error_code == "COST_GUARDRAIL_REFUSED"
        assert err.details["refused"] is True
        assert err.details["tenant_id"] == tenant_id
        assert err.details["projected_usd"] == pytest.approx(0.02)

    @pytest.mark.asyncio
    async def test_over_budget_dry_run_allows_with_dry_run_reason(self, seeded_tenant):
        pool, tenant_id, _, _ = seeded_tenant
        svc = TenantBudgetService(pool=pool)
        guardrail = CostPreflightGuardrail(
            budgets=svc,
            estimator=_FixedEstimator(0.02),  # remaining ~ 0.001 → over
            enabled=True,
            dry_run=True,  # DRY_RUN — log but allow
        )
        decision = await guardrail.check(
            tenant_id,
            model="gpt-4o",
            input_tokens=10000,
            max_output_tokens=2000,
        )
        assert decision.allowed is True
        assert decision.reason == "dry_run_over_budget"
        assert decision.dry_run is True
