"""ConversationService — thin facade over :class:`ConversationRepository`.

The repository owns SQL; the service owns the small bits of business logic
that make sense to test independently of a database (e.g., the rule that
only assistant turns may carry citations / cost / latency, or that the
title is normalised before persistence).

Current SX-4 surface keeps the service intentionally minimal: every public
method maps 1:1 to a repository call after argument normalisation. As
v1.8.1 adds operator-edit features (rename, delete, persona-pin), more
business rules will land here without changing the repository contract.
"""

from __future__ import annotations

import uuid

import structlog

from aiflow.services.conversations.repository import ConversationRepository
from aiflow.services.conversations.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    TurnAppend,
    TurnDetail,
)

__all__ = ["ConversationService"]

logger = structlog.get_logger(__name__)


class ConversationService:
    """Thin orchestration facade for the conversations persistence layer."""

    def __init__(self, repository: ConversationRepository) -> None:
        self._repo = repository

    async def create(
        self,
        *,
        tenant_id: str,
        created_by: str,
        payload: ConversationCreate,
    ) -> ConversationSummary:
        """Create a conversation. Title is left as-is (NULL → UI labels from
        first user-turn snippet)."""
        return await self._repo.create(
            tenant_id=tenant_id,
            created_by=created_by,
            payload=payload,
        )

    async def list(
        self,
        *,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSummary]:
        """Per-tenant conversation list ordered by ``updated_at DESC``."""
        return await self._repo.list(tenant_id=tenant_id, limit=limit, offset=offset)

    async def get(
        self,
        conversation_id: uuid.UUID,
        *,
        tenant_id: str,
    ) -> ConversationDetail | None:
        """Conversation + ordered turns; tenant-scoped."""
        return await self._repo.get(conversation_id, tenant_id=tenant_id)

    async def append_turn(
        self,
        conversation_id: uuid.UUID,
        *,
        tenant_id: str,
        payload: TurnAppend,
    ) -> TurnDetail | None:
        """Append a turn. Enforces the citations / cost / latency belong to
        assistant turns only invariant — user turns with non-None citations
        are rejected with a ``ValueError`` (mapped to a 422 in the router)."""
        if payload.role == "user" and (
            payload.citations is not None
            or payload.cost_usd is not None
            or payload.latency_ms is not None
        ):
            raise ValueError(
                "User turns must not carry citations, cost, or latency — "
                "those fields are reserved for assistant turns."
            )
        return await self._repo.append_turn(
            conversation_id,
            tenant_id=tenant_id,
            payload=payload,
        )

    async def delete(
        self,
        conversation_id: uuid.UUID,
        *,
        tenant_id: str,
    ) -> bool:
        """Delete a conversation (FK CASCADE drops turns). Routing for this
        method is intentionally deferred to v1.8.1; the service hook is
        ready so the v1.8.1 PR is a one-line router add."""
        return await self._repo.delete(conversation_id, tenant_id=tenant_id)
