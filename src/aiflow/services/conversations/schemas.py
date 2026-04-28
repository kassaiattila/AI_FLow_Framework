"""Pydantic v2 schemas for the aszf_conversations persistence layer.

Six external types feed the SX-4 surface:

* :class:`ConversationCreate` — write envelope used by ``POST /api/v1/conversations``.
* :class:`ConversationSummary` — list-row shape returned by ``GET /api/v1/conversations`` (no turns).
* :class:`ConversationDetail` — single-row shape returned by ``GET /api/v1/conversations/{id}`` including the
  full turn list ordered by ``turn_index ASC``.
* :class:`TurnAppend` — write envelope used by ``POST /api/v1/conversations/{id}/turns``.
* :class:`TurnDetail` — turn-row shape (citations + cost + latency live on assistant turns only).
* :class:`Citation` — shared shape with the existing chat retrieval response. The same JSON shape goes
  into ``aszf_conversation_turns.citations`` JSONB so the UI renders identically whether a turn is "live"
  (just answered) or "loaded" (from history).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Citation",
    "ConversationCreate",
    "ConversationDetail",
    "ConversationSummary",
    "PersonaLiteral",
    "RoleLiteral",
    "TurnAppend",
    "TurnDetail",
]


PersonaLiteral = Literal["baseline", "expert", "mentor"]
"""Mirrors the CHECK constraint on ``aszf_conversations.persona``."""

RoleLiteral = Literal["user", "assistant"]
"""Mirrors the CHECK constraint on ``aszf_conversation_turns.role``."""


class Citation(BaseModel):
    """Citation card payload — preserved verbatim across retrieval and persistence.

    Mirrors the shape produced by ``skills.aszf_rag_chat.workflows.query.extract_citations``
    so the UI's citation card can render the same fields regardless of whether the turn is
    being streamed live or replayed from the conversation history.
    """

    model_config = ConfigDict(extra="allow")

    source_id: str
    title: str = ""
    snippet: str = ""
    score: float = 0.0


class ConversationCreate(BaseModel):
    """Write envelope for POST /api/v1/conversations."""

    model_config = ConfigDict(extra="forbid")

    persona: PersonaLiteral = "baseline"
    collection_name: str = Field(..., min_length=1)
    title: str | None = Field(default=None, max_length=200)


class ConversationSummary(BaseModel):
    """List-row shape — returned by GET /api/v1/conversations/."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: str
    created_by: str
    persona: PersonaLiteral
    collection_name: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class TurnDetail(BaseModel):
    """Single turn — both list and detail responses share this shape."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    conversation_id: UUID
    turn_index: int = Field(..., ge=0)
    role: RoleLiteral
    content: str
    citations: list[Citation] | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    """Detail-row shape including the turn list (ordered ``turn_index ASC``)."""

    turns: list[TurnDetail] = Field(default_factory=list)


class TurnAppend(BaseModel):
    """Write envelope for POST /api/v1/conversations/{id}/turns."""

    model_config = ConfigDict(extra="forbid")

    role: RoleLiteral
    content: str = Field(..., min_length=1)
    citations: list[Citation] | None = None
    cost_usd: float | None = Field(default=None, ge=0.0)
    latency_ms: int | None = Field(default=None, ge=0)
