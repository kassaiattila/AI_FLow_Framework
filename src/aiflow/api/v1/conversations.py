"""Conversations API — Sprint X / SX-4.

Four routes scoped to ``/api/v1/conversations`` that promote the stateless
RAG retrieval into a professional management surface:

* ``GET /``              — paginated per-tenant list (sidebar).
* ``POST /``             — create a new conversation.
* ``GET /{id}``          — full detail (conversation + ordered turns).
* ``POST /{id}/turns``   — append a turn (user OR assistant).

Auth + tenant scope: the existing :class:`aiflow.api.middleware.AuthMiddleware`
enforces JWT validity at the edge. The router itself reads ``tenant_id`` from
a query parameter (default ``"default"``) — same pattern as the SX-3
``routing_runs`` router. Repository reads filter on ``tenant_id`` at the
SQL level so cross-tenant ID guesses always 404.

The retrieval API ``POST /v1/chat/completions`` is intentionally untouched
(byte-stable for UC2 MRR@5 ≥ 0.55). Per-turn citations + cost + latency are
written via the additive ``POST /api/v1/aszf/chat`` thin wrapper that lives
beside this router.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status

from aiflow.api.deps import get_pool
from aiflow.services.conversations.repository import ConversationRepository
from aiflow.services.conversations.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    TurnAppend,
    TurnDetail,
)
from aiflow.services.conversations.service import ConversationService

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


async def _service() -> ConversationService:
    pool = await get_pool()
    return ConversationService(ConversationRepository(pool))


def _resolve_created_by(request: Request, fallback: str | None) -> str:
    """Best-effort attribution: AuthMiddleware-set ``user_id`` first, then
    a query-param fallback (``"system"`` if neither is present).

    Mirrors the routing-runs router's tolerance for unauthenticated dev /
    test calls — production traffic is gated by AuthMiddleware so the
    fallback path is unreachable when auth is enforced."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    if fallback:
        return fallback
    return "system"


# ---------------------------------------------------------------------------
# GET /api/v1/conversations/  — paginated list
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[ConversationSummary])
async def list_conversations(
    tenant_id: Annotated[str, Query(description="Tenant scope (default 'default').")] = "default",
    limit: Annotated[int, Query(ge=1, le=200, description="Page size.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset.")] = 0,
) -> list[ConversationSummary]:
    """List per-tenant conversations ordered ``updated_at DESC``.

    ``limit`` is hard-capped at 200; the 422 from FastAPI's validator
    matches ``test_get_list_rejects_limit_over_200_with_422``."""
    service = await _service()
    return await service.list(tenant_id=tenant_id, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# POST /api/v1/conversations/  — create
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=ConversationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    request: Request,
    tenant_id: Annotated[str, Query(description="Tenant scope.")] = "default",
    created_by: Annotated[
        str | None,
        Query(description="Override author (test affordance; production uses JWT)."),
    ] = None,
) -> ConversationSummary:
    """Create a new conversation row.

    Persona is pinned at create-time but can be changed mid-stream by the
    operator; the change is recorded in the UI as a non-turn marker, while
    the conversation's persona field tracks the *current* persona used by
    subsequent turns."""
    service = await _service()
    author = _resolve_created_by(request, created_by)
    return await service.create(tenant_id=tenant_id, created_by=author, payload=payload)


# ---------------------------------------------------------------------------
# GET /api/v1/conversations/{id}  — detail
# ---------------------------------------------------------------------------


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    tenant_id: Annotated[str, Query(description="Tenant scope.")] = "default",
) -> ConversationDetail:
    """Detail row + full turn list ordered ``turn_index ASC``. 404 on miss
    OR cross-tenant ID collision (no leakage)."""
    service = await _service()
    detail = await service.get(conversation_id, tenant_id=tenant_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation not found: {conversation_id}",
        )
    return detail


# ---------------------------------------------------------------------------
# POST /api/v1/conversations/{id}/turns  — append turn
# ---------------------------------------------------------------------------


@router.post(
    "/{conversation_id}/turns",
    response_model=TurnDetail,
    status_code=status.HTTP_201_CREATED,
)
async def append_turn(
    conversation_id: UUID,
    payload: TurnAppend,
    tenant_id: Annotated[str, Query(description="Tenant scope.")] = "default",
) -> TurnDetail:
    """Append one turn (user OR assistant). 404 if the conversation does
    not exist or is owned by a different tenant. 422 if a user turn carries
    citations / cost / latency (those fields are reserved for assistant
    turns)."""
    service = await _service()
    try:
        turn = await service.append_turn(
            conversation_id,
            tenant_id=tenant_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if turn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation not found: {conversation_id}",
        )
    return turn
