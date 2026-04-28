"""Async repository for the aszf_conversations + aszf_conversation_turns tables.

Sibling to :class:`aiflow.services.routing_runs.repository.RoutingRunRepository` —
raw asyncpg + parameterised SQL, no SQLAlchemy ORM. Tenant scope is enforced at the
SQL level on every read so a cross-tenant ID guess returns ``None``, never the row.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg
import structlog

from aiflow.services.conversations.schemas import (
    Citation,
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    TurnAppend,
    TurnDetail,
)

__all__ = ["ConversationRepository"]

logger = structlog.get_logger(__name__)


class ConversationRepository:
    """Async repository for the SX-4 conversation persistence layer."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Conversations — write side
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        tenant_id: str,
        created_by: str,
        payload: ConversationCreate,
    ) -> ConversationSummary:
        """Insert one conversation row. Returns the created summary."""
        conversation_id = uuid.uuid4()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO aszf_conversations (
                    id, tenant_id, created_by, persona, collection_name, title
                ) VALUES (
                    $1, $2, $3, $4, $5, $6
                )
                RETURNING id, tenant_id, created_by, persona, collection_name,
                          title, created_at, updated_at
                """,
                conversation_id,
                tenant_id,
                created_by,
                payload.persona,
                payload.collection_name,
                payload.title,
            )

        logger.info(
            "conversation.created",
            conversation_id=str(conversation_id),
            tenant_id=tenant_id,
            persona=payload.persona,
            collection_name=payload.collection_name,
        )
        return _row_to_summary(row)

    # ------------------------------------------------------------------
    # Conversations — read side
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSummary]:
        """List per-tenant conversations ordered ``updated_at DESC``."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tenant_id, created_by, persona, collection_name,
                       title, created_at, updated_at
                FROM aszf_conversations
                WHERE tenant_id = $1
                ORDER BY updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                tenant_id,
                limit,
                offset,
            )
        return [_row_to_summary(r) for r in rows]

    async def get(
        self,
        conversation_id: uuid.UUID,
        *,
        tenant_id: str,
    ) -> ConversationDetail | None:
        """Fetch a conversation + its turns (``turn_index ASC``).

        Returns ``None`` on miss OR cross-tenant ID collision (no leakage)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_id, created_by, persona, collection_name,
                       title, created_at, updated_at
                FROM aszf_conversations
                WHERE id = $1 AND tenant_id = $2
                """,
                conversation_id,
                tenant_id,
            )
            if row is None:
                return None
            turn_rows = await conn.fetch(
                """
                SELECT id, conversation_id, turn_index, role, content,
                       citations, cost_usd, latency_ms, created_at
                FROM aszf_conversation_turns
                WHERE conversation_id = $1
                ORDER BY turn_index ASC
                """,
                conversation_id,
            )

        summary = _row_to_summary(row)
        return ConversationDetail(
            id=summary.id,
            tenant_id=summary.tenant_id,
            created_by=summary.created_by,
            persona=summary.persona,
            collection_name=summary.collection_name,
            title=summary.title,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
            turns=[_row_to_turn(r) for r in turn_rows],
        )

    # ------------------------------------------------------------------
    # Turns — write side
    # ------------------------------------------------------------------

    async def append_turn(
        self,
        conversation_id: uuid.UUID,
        *,
        tenant_id: str,
        payload: TurnAppend,
    ) -> TurnDetail | None:
        """Append one turn. Returns ``None`` if the conversation does not exist
        (or is owned by a different tenant — same response so attackers cannot
        distinguish "not found" from "cross-tenant").

        Uses a single atomic transaction:

        1. Verify the parent conversation exists and is tenant-scoped.
        2. SELECT the next ``turn_index`` (``MAX(turn_index)+1`` or 0).
        3. INSERT the turn.
        4. Bump the parent's ``updated_at`` so the sidebar list reorders.
        """
        citations_json = (
            json.dumps([c.model_dump(mode="json") for c in payload.citations])
            if payload.citations is not None
            else None
        )
        turn_id = uuid.uuid4()

        async with self._pool.acquire() as conn, conn.transaction():
            parent = await conn.fetchrow(
                """
                    SELECT id FROM aszf_conversations
                    WHERE id = $1 AND tenant_id = $2
                    FOR UPDATE
                    """,
                conversation_id,
                tenant_id,
            )
            if parent is None:
                return None

            next_index_row = await conn.fetchrow(
                """
                    SELECT COALESCE(MAX(turn_index) + 1, 0) AS next_index
                    FROM aszf_conversation_turns
                    WHERE conversation_id = $1
                    """,
                conversation_id,
            )
            next_index = int(next_index_row["next_index"])

            inserted = await conn.fetchrow(
                """
                    INSERT INTO aszf_conversation_turns (
                        id, conversation_id, turn_index, role, content,
                        citations, cost_usd, latency_ms
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6::jsonb, $7, $8
                    )
                    RETURNING id, conversation_id, turn_index, role, content,
                              citations, cost_usd, latency_ms, created_at
                    """,
                turn_id,
                conversation_id,
                next_index,
                payload.role,
                payload.content,
                citations_json,
                payload.cost_usd,
                payload.latency_ms,
            )

            await conn.execute(
                """
                    UPDATE aszf_conversations
                    SET updated_at = NOW()
                    WHERE id = $1
                    """,
                conversation_id,
            )

        logger.info(
            "conversation.turn_appended",
            conversation_id=str(conversation_id),
            turn_id=str(turn_id),
            tenant_id=tenant_id,
            role=payload.role,
            turn_index=next_index,
            cost_usd=payload.cost_usd,
            latency_ms=payload.latency_ms,
        )
        return _row_to_turn(inserted)

    # ------------------------------------------------------------------
    # Conversations — delete (deferred behind service-level method)
    # ------------------------------------------------------------------

    async def delete(
        self,
        conversation_id: uuid.UUID,
        *,
        tenant_id: str,
    ) -> bool:
        """Delete one conversation (cascades to turns). Returns True if a row
        was actually deleted, False on miss / cross-tenant. The DELETE route
        itself is intentionally deferred to v1.8.1; this method is exposed
        for future use + integration tests that exercise FK CASCADE."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM aszf_conversations
                WHERE id = $1 AND tenant_id = $2
                """,
                conversation_id,
                tenant_id,
            )
        # asyncpg returns "DELETE N" — parse the row count
        try:
            count = int(result.split()[-1])
        except (ValueError, IndexError):
            count = 0
        return count > 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_summary(row: asyncpg.Record) -> ConversationSummary:
    return ConversationSummary(
        id=row["id"],
        tenant_id=row["tenant_id"],
        created_by=row["created_by"],
        persona=row["persona"],
        collection_name=row["collection_name"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_turn(row: asyncpg.Record) -> TurnDetail:
    raw_citations = row["citations"]
    citations: list[Citation] | None
    if raw_citations is None:
        citations = None
    else:
        if isinstance(raw_citations, str):
            try:
                parsed: Any = json.loads(raw_citations)
            except (TypeError, ValueError):
                parsed = None
        else:
            parsed = raw_citations
        if isinstance(parsed, list):
            citations = [Citation.model_validate(c) for c in parsed if isinstance(c, dict)]
        else:
            citations = None

    return TurnDetail(
        id=row["id"],
        conversation_id=row["conversation_id"],
        turn_index=row["turn_index"],
        role=row["role"],
        content=row["content"],
        citations=citations,
        cost_usd=row["cost_usd"],
        latency_ms=row["latency_ms"],
        created_at=row["created_at"],
    )
