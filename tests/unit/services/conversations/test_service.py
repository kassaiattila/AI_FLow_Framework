"""
@test_registry:
    suite: core-unit
    component: services.conversations
    covers:
        - src/aiflow/services/conversations/repository.py
        - src/aiflow/services/conversations/service.py
        - src/aiflow/services/conversations/schemas.py
    phase: v1.8.0
    priority: high
    estimated_duration_ms: 60
    requires_services: []
    tags: [unit, services, conversations, sprint_x, sx_4]
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.conversations.repository import ConversationRepository
from aiflow.services.conversations.schemas import (
    Citation,
    ConversationCreate,
    TurnAppend,
)
from aiflow.services.conversations.service import ConversationService

# ---------------------------------------------------------------------------
# Fixtures — mocked asyncpg pool / connection
# ---------------------------------------------------------------------------


def _make_record(payload: dict) -> MagicMock:
    """Mimic asyncpg.Record's ``__getitem__`` access pattern."""
    rec = MagicMock()
    rec.__getitem__.side_effect = lambda key: payload[key]
    return rec


def _build_conversation_row(
    *,
    conversation_id: uuid.UUID | None = None,
    tenant_id: str = "default",
    created_by: str = "user-1",
    persona: str = "baseline",
    collection_name: str = "azhu-test",
    title: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> dict:
    now = datetime.now(UTC)
    return {
        "id": conversation_id or uuid.uuid4(),
        "tenant_id": tenant_id,
        "created_by": created_by,
        "persona": persona,
        "collection_name": collection_name,
        "title": title,
        "created_at": created_at or now,
        "updated_at": updated_at or now,
    }


def _build_turn_row(
    *,
    conversation_id: uuid.UUID,
    turn_index: int,
    role: str = "user",
    content: str = "Mi a panaszkezelési határidő?",
    citations: list[dict] | None = None,
    cost_usd: float | None = None,
    latency_ms: int | None = None,
    created_at: datetime | None = None,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "conversation_id": conversation_id,
        "turn_index": turn_index,
        "role": role,
        "content": content,
        "citations": json.dumps(citations) if citations is not None else None,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "created_at": created_at or datetime.now(UTC),
    }


class _FakeTransaction:
    async def __aenter__(self) -> _FakeTransaction:
        return self

    async def __aexit__(self, *_a: object) -> None:
        return None


def _fake_pool(
    *,
    fetchrow_side_effect: list | None = None,
    fetch_side_effect: list | None = None,
    execute_return: str = "INSERT 0 1",
) -> tuple[MagicMock, dict]:
    """Build a mocked asyncpg.Pool whose ``acquire()`` yields a connection
    that pulls fetchrow / fetch results from FIFO queues.

    Records every fetchrow / fetch / execute call site (SQL + args) into
    ``captured`` so tests can assert on the persisted contract.
    """
    captured: dict = {"fetchrow": [], "fetch": [], "execute": []}
    fetchrow_queue = list(fetchrow_side_effect or [])
    fetch_queue = list(fetch_side_effect or [])

    fake_conn = MagicMock()

    async def fake_fetchrow(*args, **kwargs):
        captured["fetchrow"].append((args, kwargs))
        if not fetchrow_queue:
            return None
        result = fetchrow_queue.pop(0)
        if isinstance(result, dict):
            return _make_record(result)
        return result

    async def fake_fetch(*args, **kwargs):
        captured["fetch"].append((args, kwargs))
        if not fetch_queue:
            return []
        rows = fetch_queue.pop(0)
        return [_make_record(r) if isinstance(r, dict) else r for r in rows]

    async def fake_execute(*args, **kwargs):
        captured["execute"].append((args, kwargs))
        return execute_return

    fake_conn.fetchrow = AsyncMock(side_effect=fake_fetchrow)
    fake_conn.fetch = AsyncMock(side_effect=fake_fetch)
    fake_conn.execute = AsyncMock(side_effect=fake_execute)
    fake_conn.transaction = MagicMock(return_value=_FakeTransaction())

    fake_acquire_cm = MagicMock()
    fake_acquire_cm.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_acquire_cm.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=fake_acquire_cm)
    return pool, captured


# ---------------------------------------------------------------------------
# 1. test_create_returns_uuid_and_persists
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_uuid_and_persists(self):
        row = _build_conversation_row(persona="expert", collection_name="azhu-test")
        pool, captured = _fake_pool(fetchrow_side_effect=[row])
        service = ConversationService(ConversationRepository(pool))

        summary = await service.create(
            tenant_id="acme",
            created_by="user-1",
            payload=ConversationCreate(persona="expert", collection_name="azhu-test"),
        )

        assert summary.id == row["id"]
        assert summary.persona == "expert"
        assert summary.collection_name == "azhu-test"
        # SQL contract: INSERT into aszf_conversations RETURNING the row
        sql, *args = captured["fetchrow"][0][0]
        assert "INSERT INTO aszf_conversations" in sql
        assert "RETURNING" in sql
        assert args[1] == "acme"
        assert args[2] == "user-1"
        assert args[3] == "expert"
        assert args[4] == "azhu-test"
        assert args[5] is None  # title

    # ---------------------------------------------------------------------
    # 2. test_create_defaults_title_to_null
    # ---------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_defaults_title_to_null(self):
        row = _build_conversation_row(title=None)
        pool, captured = _fake_pool(fetchrow_side_effect=[row])
        service = ConversationService(ConversationRepository(pool))

        summary = await service.create(
            tenant_id="default",
            created_by="user-1",
            payload=ConversationCreate(collection_name="azhu-test"),
        )

        assert summary.title is None
        # Persisted title arg is None
        args = captured["fetchrow"][0][0][1:]
        assert args[5] is None


# ---------------------------------------------------------------------------
# 3. test_list_filters_by_tenant_isolates_correctly
# ---------------------------------------------------------------------------


class TestList:
    @pytest.mark.asyncio
    async def test_list_filters_by_tenant_isolates_correctly(self):
        # Repository returns ONLY rows for the queried tenant — caller is
        # the gatekeeper. Verify the WHERE clause carries tenant_id and
        # that the query parameter mirrors the request.
        pool, captured = _fake_pool(
            fetch_side_effect=[
                [
                    _build_conversation_row(tenant_id="acme"),
                    _build_conversation_row(tenant_id="acme"),
                ],
            ],
        )
        service = ConversationService(ConversationRepository(pool))

        rows = await service.list(tenant_id="acme")

        assert all(r.tenant_id == "acme" for r in rows)
        sql, *args = captured["fetch"][0][0]
        assert "WHERE tenant_id = $1" in sql
        assert args[0] == "acme"

    # ---------------------------------------------------------------------
    # 4. test_list_orders_by_updated_at_desc
    # ---------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_orders_by_updated_at_desc(self):
        now = datetime.now(UTC)
        # Repository preserves SQL-level ordering — we verify the SQL string
        # carries ORDER BY updated_at DESC and the rows arrive in that order.
        pool, captured = _fake_pool(
            fetch_side_effect=[
                [
                    _build_conversation_row(updated_at=now),
                    _build_conversation_row(updated_at=now - timedelta(hours=1)),
                    _build_conversation_row(updated_at=now - timedelta(hours=2)),
                ],
            ],
        )
        service = ConversationService(ConversationRepository(pool))

        rows = await service.list(tenant_id="default")

        assert len(rows) == 3
        assert rows[0].updated_at >= rows[1].updated_at >= rows[2].updated_at
        sql = captured["fetch"][0][0][0]
        assert "ORDER BY updated_at DESC" in sql


# ---------------------------------------------------------------------------
# 5. test_get_includes_turns_in_index_order
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_includes_turns_in_index_order(self):
        conversation_id = uuid.uuid4()
        conv_row = _build_conversation_row(conversation_id=conversation_id)
        turn_rows = [
            _build_turn_row(
                conversation_id=conversation_id,
                turn_index=0,
                role="user",
                content="kerdes",
            ),
            _build_turn_row(
                conversation_id=conversation_id,
                turn_index=1,
                role="assistant",
                content="valasz",
                citations=[
                    {
                        "source_id": "doc-1",
                        "title": "ASZF",
                        "snippet": "...",
                        "score": 0.91,
                    }
                ],
                cost_usd=0.0042,
                latency_ms=312,
            ),
        ]
        pool, captured = _fake_pool(
            fetchrow_side_effect=[conv_row],
            fetch_side_effect=[turn_rows],
        )
        service = ConversationService(ConversationRepository(pool))

        detail = await service.get(conversation_id, tenant_id="default")

        assert detail is not None
        assert len(detail.turns) == 2
        assert [t.turn_index for t in detail.turns] == [0, 1]
        assert detail.turns[0].role == "user"
        assert detail.turns[1].role == "assistant"
        assert detail.turns[1].citations is not None
        assert len(detail.turns[1].citations) == 1
        assert detail.turns[1].citations[0].source_id == "doc-1"
        # Turn fetch SQL carries the index-ordered clause
        turn_sql = captured["fetch"][0][0][0]
        assert "ORDER BY turn_index ASC" in turn_sql

    # ---------------------------------------------------------------------
    # 6. test_get_returns_none_for_other_tenant
    # ---------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_returns_none_for_other_tenant(self):
        # Repository returns None when the tenant-scoped fetchrow misses,
        # never leaking turns or surface fields.
        conversation_id = uuid.uuid4()
        pool, captured = _fake_pool(fetchrow_side_effect=[None])
        service = ConversationService(ConversationRepository(pool))

        detail = await service.get(conversation_id, tenant_id="acme")

        assert detail is None
        # No turn fetch attempted — we MUST not query turns for a missed
        # conversation row
        assert captured["fetch"] == []
        # Conversation fetch SQL carries the tenant clause
        sql = captured["fetchrow"][0][0][0]
        assert "WHERE id = $1 AND tenant_id = $2" in sql


# ---------------------------------------------------------------------------
# 7. test_append_turn_increments_turn_index
# ---------------------------------------------------------------------------


class TestAppendTurn:
    @pytest.mark.asyncio
    async def test_append_turn_increments_turn_index(self):
        conversation_id = uuid.uuid4()
        # Repository sequence:
        #   1. SELECT parent (FOR UPDATE) -> exists
        #   2. SELECT MAX(turn_index)+1   -> 3
        #   3. INSERT turn returning row  -> the inserted turn
        new_turn_row = _build_turn_row(
            conversation_id=conversation_id,
            turn_index=3,
            role="user",
            content="harmadik kerdes",
        )
        pool, captured = _fake_pool(
            fetchrow_side_effect=[
                {"id": conversation_id},
                {"next_index": 3},
                new_turn_row,
            ],
        )
        service = ConversationService(ConversationRepository(pool))

        turn = await service.append_turn(
            conversation_id,
            tenant_id="default",
            payload=TurnAppend(role="user", content="harmadik kerdes"),
        )

        assert turn is not None
        assert turn.turn_index == 3
        # The next-index SQL carries COALESCE(MAX(...) + 1, 0)
        next_index_sql = captured["fetchrow"][1][0][0]
        assert "COALESCE(MAX(turn_index) + 1, 0)" in next_index_sql
        # The INSERT carries the resolved index
        insert_args = captured["fetchrow"][2][0][1:]
        assert insert_args[2] == 3  # turn_index positional

    # ---------------------------------------------------------------------
    # 8. test_append_turn_updates_parent_updated_at
    # ---------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_append_turn_updates_parent_updated_at(self):
        conversation_id = uuid.uuid4()
        pool, captured = _fake_pool(
            fetchrow_side_effect=[
                {"id": conversation_id},
                {"next_index": 0},
                _build_turn_row(conversation_id=conversation_id, turn_index=0),
            ],
        )
        service = ConversationService(ConversationRepository(pool))

        await service.append_turn(
            conversation_id,
            tenant_id="default",
            payload=TurnAppend(role="user", content="hello"),
        )

        # An UPDATE on aszf_conversations.updated_at MUST run after insert.
        update_calls = [c for c in captured["execute"] if "UPDATE aszf_conversations" in c[0][0]]
        assert len(update_calls) == 1
        assert "SET updated_at = NOW()" in update_calls[0][0][0]
        assert update_calls[0][0][1] == conversation_id

    # ---------------------------------------------------------------------
    # 9. test_append_turn_rejects_cross_tenant
    # ---------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_append_turn_rejects_cross_tenant(self):
        conversation_id = uuid.uuid4()
        # Parent SELECT misses because tenant_id does not match — service
        # returns None, no insert, no update.
        pool, captured = _fake_pool(fetchrow_side_effect=[None])
        service = ConversationService(ConversationRepository(pool))

        result = await service.append_turn(
            conversation_id,
            tenant_id="other-tenant",
            payload=TurnAppend(role="user", content="payload"),
        )

        assert result is None
        # Only the parent SELECT ran — no INSERT, no UPDATE
        assert len(captured["fetchrow"]) == 1
        assert captured["execute"] == []
        sql = captured["fetchrow"][0][0][0]
        assert "WHERE id = $1 AND tenant_id = $2" in sql

    @pytest.mark.asyncio
    async def test_append_turn_rejects_user_with_citations(self):
        # Service-level invariant: user turns cannot carry citations.
        # Repository must NEVER be reached on this path.
        pool, captured = _fake_pool()
        service = ConversationService(ConversationRepository(pool))

        with pytest.raises(ValueError, match="assistant turns"):
            await service.append_turn(
                uuid.uuid4(),
                tenant_id="default",
                payload=TurnAppend(
                    role="user",
                    content="x",
                    citations=[Citation(source_id="doc-1")],
                ),
            )

        assert captured["fetchrow"] == []
        assert captured["execute"] == []
