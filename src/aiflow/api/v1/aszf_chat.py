"""ASZF chat thin wrapper — Sprint X / SX-4.

Exposes the existing ``aszf_rag_chat`` workflow under a stable JSON shape
that includes ``citations`` + ``cost_usd`` + ``latency_ms`` so the SX-4
``/aszf/chat`` admin UI can render the citation card and cost meter
without parsing the OpenAI-compatible ``ChatCompletionResponse`` from
``POST /v1/chat/completions``.

This route is **additive**:

* The OpenAI-compatible ``POST /v1/chat/completions`` is **untouched**.
  UC2 MRR@5 ≥ 0.55 byte-stable. External clients that already use the
  OpenAI shape continue to work.
* New callers (the SX-4 UI, or any tool that needs structured citations)
  use this endpoint.

The endpoint's wire format is intentionally minimal — it surfaces only
the fields the SX-4 UI consumes. If a future sprint needs the full
hallucination score / sources / search_results payload, those can be
added without breaking this contract.
"""

from __future__ import annotations

import time
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from aiflow.services.conversations.schemas import Citation, PersonaLiteral

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/aszf", tags=["aszf-chat"])


class AszfChatRequest(BaseModel):
    """Single-turn request envelope.

    ``conversation_history`` is the *prior* turns (excluding the question
    being asked); the workflow's `rewrite_query` step uses it for context
    expansion. The repository persists the history independently — this
    endpoint is stateless on the server side."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    collection: str = Field(..., min_length=1)
    persona: PersonaLiteral = "baseline"
    language: str = Field(default="hu")
    top_k: int = Field(default=5, ge=1, le=20)
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class AszfChatResponse(BaseModel):
    """Response envelope — answer + structured citations + observability."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: int = Field(default=0, ge=0)
    persona: PersonaLiteral = "baseline"
    collection: str = ""
    hallucination_score: float | None = None


@router.post("/chat", response_model=AszfChatResponse)
async def aszf_chat(
    request: AszfChatRequest,
    tenant_id: Annotated[
        str,
        Query(description="Tenant scope (forwarded to the workflow for tenant-scoped retrieval)."),
    ] = "default",
) -> AszfChatResponse:
    """Run the ASZF RAG workflow and return ``answer`` + structured
    ``citations`` + observability fields.

    Imports the workflow lazily so the API process does not pay the
    ``skills.aszf_rag_chat`` import cost on cold-start when the chat
    endpoint is unused (matches the existing
    :func:`aiflow.api.v1.chat_completions._run_aszf_rag` pattern)."""
    from skills.aszf_rag_chat.workflows.query import (
        build_context,
        detect_hallucination,
        extract_citations,
        generate_answer,
        rewrite_query,
        search_documents,
    )

    started_at = time.monotonic()
    data: dict[str, Any] = {
        "question": request.question,
        "collection": request.collection,
        "role": request.persona,
        "language": request.language,
        "conversation_history": request.conversation_history,
        "top_k": request.top_k,
        "tenant_id": tenant_id,
    }

    try:
        r1 = await rewrite_query(data)
        r2 = await search_documents({**data, **r1})
        r3 = await build_context({**data, **r2})
        r4 = await generate_answer({**data, **r3})
        r5 = await extract_citations(r4)
        r6 = await detect_hallucination(r5)
    except Exception as exc:
        logger.error(
            "aszf_chat.workflow_error",
            tenant_id=tenant_id,
            collection=request.collection,
            persona=request.persona,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Workflow error: {exc}") from exc

    latency_ms = int((time.monotonic() - started_at) * 1000)
    answer = str(r6.get("answer") or "")
    raw_citations = r6.get("citations") or []
    citations: list[Citation] = []
    for c in raw_citations:
        if isinstance(c, dict):
            citations.append(Citation.model_validate(c))

    cost_usd = float(r6.get("cost_usd") or 0.0)
    hallucination_score = r6.get("hallucination_score")
    try:
        hallucination_score_f: float | None = (
            float(hallucination_score) if hallucination_score is not None else None
        )
    except (TypeError, ValueError):
        hallucination_score_f = None

    logger.info(
        "aszf_chat.done",
        tenant_id=tenant_id,
        collection=request.collection,
        persona=request.persona,
        answer_len=len(answer),
        citations=len(citations),
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )

    return AszfChatResponse(
        answer=answer,
        citations=citations,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        persona=request.persona,
        collection=request.collection,
        hallucination_score=hallucination_score_f,
    )
