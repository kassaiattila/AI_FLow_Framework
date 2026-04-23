"""Integration test — PolicyEngine.cost_cap enforcement against real PostgreSQL.

@test_registry
suite: integration-policy
component: policy.engine.enforce_cost_cap
covers: [src/aiflow/policy/engine.py, src/aiflow/state/cost_repository.py, alembic/versions/043_cost_attribution_tenant.py]
phase: v1.4.8
priority: high
requires_services: [postgres]
tags: [integration, policy, cost_cap, sprint_l, s112, postgres]

Exercises Sprint L / S112 — ``CostCapBreached`` is raised iff the tenant's
running cost over the configured window reaches the cap. Scenario:

1. Seed tenant cap = $0.001 via ``PolicyConfig``.
2. Insert a single ``CostAttribution`` of $0.0005 → still below cap →
   ``enforce_cost_cap`` passes and returns the running cost.
3. Insert a second $0.0007 attribution → cumulative $0.0012 ≥ cap →
   ``enforce_cost_cap`` raises ``CostCapBreached`` with structured details.

SOHA NE mock — real asyncpg pool against Docker PostgreSQL (port 5433).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import asyncpg
import pytest
import pytest_asyncio

from aiflow.contracts.cost_attribution import CostAttribution
from aiflow.core.errors import CostCapBreached
from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine
from aiflow.state.cost_repository import CostAttributionRepository

pytestmark = pytest.mark.integration


def _resolve_db_url() -> str:
    raw = os.getenv(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return raw.replace("postgresql+asyncpg://", "postgresql://")


@pytest_asyncio.fixture
async def pool():
    """Fresh asyncpg pool per test. Cleans up cost_records rows for the test tenant."""
    url = _resolve_db_url()
    try:
        p = await asyncpg.create_pool(url, min_size=1, max_size=3)
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    # Make sure Alembic 043 actually ran (tenant_id column must exist on cost_records).
    async with p.acquire() as conn:
        col = await conn.fetchrow(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'cost_records' AND column_name = 'tenant_id'
            """
        )
        if col is None:
            await p.close()
            pytest.skip("cost_records.tenant_id column missing — run `alembic upgrade head`.")

    tenant_id = f"s112-cap-test-{uuid.uuid4().hex[:8]}"

    yield p, tenant_id

    try:
        async with p.acquire() as conn:
            await conn.execute("DELETE FROM cost_records WHERE tenant_id = $1", tenant_id)
    finally:
        await p.close()


async def _insert_attr(repo: CostAttributionRepository, tenant_id: str, cost_usd: float) -> None:
    await repo.insert_attribution(
        CostAttribution(
            tenant_id=tenant_id,
            skill="rag_engine",
            provider="openai",
            model="text-embedding-3-small",
            input_tokens=100,
            output_tokens=0,
            cost_usd=cost_usd,
            recorded_at=datetime.now(UTC),
        )
    )


class TestCostCapEnforcement:
    @pytest.mark.asyncio
    async def test_first_call_passes_second_call_breaches(self, pool):
        p, tenant_id = pool
        repo = CostAttributionRepository(p)

        engine = PolicyEngine(
            profile_config=PolicyConfig(cost_cap_usd=0.001, cost_cap_window_h=1),
        )

        # Call 1 — under cap, passes and returns running cost 0.0
        running = await engine.enforce_cost_cap(tenant_id=tenant_id, pool=p)
        assert running == 0.0

        # Record first cost below cap
        await _insert_attr(repo, tenant_id, 0.0005)

        running = await engine.enforce_cost_cap(tenant_id=tenant_id, pool=p)
        assert 0.00049 <= running <= 0.00051

        # Record second cost — cumulative now 0.0012 >= cap 0.001
        await _insert_attr(repo, tenant_id, 0.0007)

        # Call 2 — breaches, raises CostCapBreached carrying structured context
        with pytest.raises(CostCapBreached) as exc_info:
            await engine.enforce_cost_cap(tenant_id=tenant_id, pool=p)

        err = exc_info.value
        assert err.tenant_id == tenant_id
        assert err.cap_usd == pytest.approx(0.001)
        assert err.current_usd >= 0.001
        assert err.window_h == 1
        assert err.http_status == 429
        assert err.error_code == "COST_CAP_BREACHED"
        assert err.details["tenant_id"] == tenant_id

    @pytest.mark.asyncio
    async def test_no_cap_configured_returns_zero(self, pool):
        """enforce_cost_cap is a no-op when cost_cap_usd is None (default)."""
        p, tenant_id = pool
        repo = CostAttributionRepository(p)

        await _insert_attr(repo, tenant_id, 999.0)

        engine = PolicyEngine(profile_config=PolicyConfig())  # cost_cap_usd = None
        running = await engine.enforce_cost_cap(tenant_id=tenant_id, pool=p)
        assert running == 0.0

    @pytest.mark.asyncio
    async def test_aggregate_respects_tenant_isolation(self, pool):
        """A different tenant's cost must not count against this tenant's cap."""
        p, tenant_id = pool
        repo = CostAttributionRepository(p)

        other_tenant = f"s112-other-{uuid.uuid4().hex[:8]}"
        try:
            await _insert_attr(repo, other_tenant, 10.0)

            engine = PolicyEngine(
                profile_config=PolicyConfig(cost_cap_usd=0.001, cost_cap_window_h=1),
            )
            # Our tenant has no cost records → still passes.
            running = await engine.enforce_cost_cap(tenant_id=tenant_id, pool=p)
            assert running == 0.0
        finally:
            async with p.acquire() as conn:
                await conn.execute("DELETE FROM cost_records WHERE tenant_id = $1", other_tenant)
