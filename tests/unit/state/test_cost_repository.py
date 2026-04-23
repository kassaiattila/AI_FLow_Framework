"""
@test_registry:
    suite: core-unit
    component: state.cost_repository
    covers: [src/aiflow/state/cost_repository.py]
    phase: v1.4.8
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [state, cost_repository, async, sprint_l, s112]
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.contracts.cost_attribution import CostAttribution
from aiflow.state.cost_repository import CostAttributionRepository


def _make_pool() -> tuple[MagicMock, AsyncMock]:
    """Build an asyncpg-shaped mock pool whose ``acquire()`` yields a conn mock."""
    conn = AsyncMock()
    pool = MagicMock()

    # ``async with pool.acquire() as conn`` — acquire() returns an async ctx mgr,
    # NOT a coroutine. MagicMock's __aenter__/__aexit__ cover this cleanly.
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=ctx)
    return pool, conn


def _attr(**overrides) -> CostAttribution:
    base = dict(
        tenant_id="acme",
        skill="rag_engine",
        provider="openai",
        model="text-embedding-3-small",
        input_tokens=100,
        output_tokens=0,
        cost_usd=0.0005,
        recorded_at=datetime(2026, 4, 24, tzinfo=UTC),
    )
    base.update(overrides)
    return CostAttribution(**base)


class TestCostAttributionRepositoryInsert:
    @pytest.mark.asyncio
    async def test_insert_with_valid_run_id_parses_uuid(self):
        pool, conn = _make_pool()
        repo = CostAttributionRepository(pool)
        run_uuid = uuid.uuid4()
        await repo.insert_attribution(_attr(run_id=str(run_uuid)))

        conn.execute.assert_awaited_once()
        args = conn.execute.await_args.args
        # args[0]=sql, then positional: $1=id, $2=workflow_run_id, $3=step_name ...
        assert isinstance(args[0], str)
        assert args[2] == run_uuid  # parsed UUID kept as UUID, not str

    @pytest.mark.asyncio
    async def test_insert_with_missing_run_id_passes_none(self):
        pool, conn = _make_pool()
        repo = CostAttributionRepository(pool)
        await repo.insert_attribution(_attr(run_id=None))

        args = conn.execute.await_args.args
        assert args[2] is None

    @pytest.mark.asyncio
    async def test_insert_with_invalid_run_id_falls_back_to_none(self):
        """Malformed run_id shouldn't block cost recording — best-effort path."""
        pool, conn = _make_pool()
        repo = CostAttributionRepository(pool)
        await repo.insert_attribution(_attr(run_id="not-a-uuid"))

        args = conn.execute.await_args.args
        assert args[2] is None

    @pytest.mark.asyncio
    async def test_insert_forwards_tenant_and_cost_fields(self):
        pool, conn = _make_pool()
        repo = CostAttributionRepository(pool)
        await repo.insert_attribution(_attr(tenant_id="tenant-42", cost_usd=1.23))

        args = conn.execute.await_args.args
        # Order: sql, id, run, skill, model, provider, in_tok, out_tok, cost, tenant, recorded
        assert args[3] == "rag_engine"
        assert args[8] == 1.23
        assert args[9] == "tenant-42"


class TestCostAttributionRepositoryAggregate:
    @pytest.mark.asyncio
    async def test_aggregate_returns_float_from_row(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value={"total": 2.5})
        repo = CostAttributionRepository(pool)

        total = await repo.aggregate_running_cost("acme", 1)
        assert total == 2.5

    @pytest.mark.asyncio
    async def test_aggregate_coerces_none_to_zero(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value={"total": None})
        repo = CostAttributionRepository(pool)

        total = await repo.aggregate_running_cost("acme", 24)
        assert total == 0.0

    @pytest.mark.asyncio
    async def test_aggregate_handles_missing_row(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        repo = CostAttributionRepository(pool)

        total = await repo.aggregate_running_cost("acme", 1)
        assert total == 0.0
