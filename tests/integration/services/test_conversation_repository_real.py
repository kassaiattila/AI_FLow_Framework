"""
@test_registry:
    suite: integration-services
    component: services.conversations.repository
    covers:
        - src/aiflow/services/conversations/repository.py
        - alembic/versions/051_aszf_conversations.py
    phase: v1.8.0
    priority: high
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, conversations, sprint_x, sx_4]

Sprint X / SX-4 — round-trip repository tests against real PostgreSQL
(Docker 5433). Verifies the Alembic 051 schema, the FK CASCADE on
``aszf_conversation_turns``, and the ``updated_at`` trigger-equivalent
write path. Skips cleanly when PG is unavailable so the unit suite
still runs in environments without Docker.
"""

from __future__ import annotations

import os
import uuid

import asyncpg
import pytest

from aiflow.api import deps
from aiflow.api.deps import get_pool
from aiflow.services.conversations.repository import ConversationRepository
from aiflow.services.conversations.schemas import (
    Citation,
    ConversationCreate,
    TurnAppend,
)

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)


@pytest.fixture(autouse=True)
async def _reset_deps_pool():
    """Reset cached pool after each test (asyncpg + event-loop trap)."""
    yield
    await deps.close_all()


async def _ensure_pg_available() -> bool:
    raw = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(raw, timeout=2)
        await conn.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'aszf_conversations'
            """
        )
        await conn.close()
    except Exception:
        return False
    return True


@pytest.fixture
async def repo() -> ConversationRepository:
    if not await _ensure_pg_available():
        pytest.skip("PostgreSQL with aszf_conversations table unavailable (run Alembic 051).")
    pool = await get_pool()
    return ConversationRepository(pool)


# ---------------------------------------------------------------------------
# 1. test_create_then_append_then_list_real_pg
# ---------------------------------------------------------------------------


async def test_create_then_append_then_list_real_pg(repo: ConversationRepository):
    """End-to-end happy path: create a conversation, append a user + an
    assistant turn (with citations + cost + latency), then verify the
    parent's ``updated_at`` advanced and the detail GET returns the
    turns in turn-index order with citations preserved."""
    tenant = f"sx4-rt-{uuid.uuid4()}"
    summary = await repo.create(
        tenant_id=tenant,
        created_by="user-1",
        payload=ConversationCreate(
            persona="baseline",
            collection_name="azhu-test",
        ),
    )
    assert summary.tenant_id == tenant
    assert summary.persona == "baseline"
    initial_updated_at = summary.updated_at

    user_turn = await repo.append_turn(
        summary.id,
        tenant_id=tenant,
        payload=TurnAppend(role="user", content="Mi a panaszkezelési hatarido?"),
    )
    assert user_turn is not None
    assert user_turn.turn_index == 0
    assert user_turn.role == "user"

    assistant_turn = await repo.append_turn(
        summary.id,
        tenant_id=tenant,
        payload=TurnAppend(
            role="assistant",
            content="A panaszkezelési hatarido 30 nap.",
            citations=[
                Citation(
                    source_id="doc-1",
                    title="ASZF",
                    snippet="A panaszt 30 napon belul...",
                    score=0.91,
                ),
            ],
            cost_usd=0.0042,
            latency_ms=312,
        ),
    )
    assert assistant_turn is not None
    assert assistant_turn.turn_index == 1
    assert assistant_turn.role == "assistant"
    assert assistant_turn.citations is not None
    assert len(assistant_turn.citations) == 1
    assert assistant_turn.citations[0].source_id == "doc-1"
    assert assistant_turn.cost_usd == pytest.approx(0.0042)
    assert assistant_turn.latency_ms == 312

    # Detail read brings back both turns in index order.
    detail = await repo.get(summary.id, tenant_id=tenant)
    assert detail is not None
    assert [t.turn_index for t in detail.turns] == [0, 1]
    assert detail.turns[1].citations is not None
    assert detail.turns[1].citations[0].score == pytest.approx(0.91)
    # Updated-at advanced past the create-time mark.
    assert detail.updated_at >= initial_updated_at

    # List honours tenant scope.
    rows = await repo.list(tenant_id=tenant)
    assert len(rows) == 1
    assert rows[0].id == summary.id

    # Cross-tenant guard: another tenant cannot see the row.
    other_rows = await repo.list(tenant_id=f"{tenant}-other")
    assert other_rows == []
    assert await repo.get(summary.id, tenant_id=f"{tenant}-other") is None


# ---------------------------------------------------------------------------
# 2. test_cascade_delete_drops_turns_real_pg
# ---------------------------------------------------------------------------


async def test_cascade_delete_drops_turns_real_pg(repo: ConversationRepository):
    """Deleting a conversation must cascade-delete its turns (FK
    ON DELETE CASCADE). Verifies the migration's FK contract directly."""
    tenant = f"sx4-cascade-{uuid.uuid4()}"
    summary = await repo.create(
        tenant_id=tenant,
        created_by="user-1",
        payload=ConversationCreate(persona="baseline", collection_name="azhu-test"),
    )
    await repo.append_turn(
        summary.id,
        tenant_id=tenant,
        payload=TurnAppend(role="user", content="kerdes"),
    )
    await repo.append_turn(
        summary.id,
        tenant_id=tenant,
        payload=TurnAppend(
            role="assistant",
            content="valasz",
            cost_usd=0.001,
            latency_ms=100,
        ),
    )

    # Pre-delete: 2 turns visible
    detail = await repo.get(summary.id, tenant_id=tenant)
    assert detail is not None
    assert len(detail.turns) == 2

    deleted = await repo.delete(summary.id, tenant_id=tenant)
    assert deleted is True

    # Post-delete: detail returns None; turns are gone (FK CASCADE)
    assert await repo.get(summary.id, tenant_id=tenant) is None
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS n FROM aszf_conversation_turns WHERE conversation_id = $1",
            summary.id,
        )
        assert int(row["n"]) == 0

    # Cross-tenant delete is a no-op.
    summary2 = await repo.create(
        tenant_id=tenant,
        created_by="user-1",
        payload=ConversationCreate(persona="baseline", collection_name="azhu-test"),
    )
    deleted_other = await repo.delete(summary2.id, tenant_id=f"{tenant}-other")
    assert deleted_other is False
    # Original row still present.
    assert await repo.get(summary2.id, tenant_id=tenant) is not None
