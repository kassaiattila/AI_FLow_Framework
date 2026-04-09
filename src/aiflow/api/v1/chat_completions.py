"""OpenAI-compatible chat completions API endpoint.

This is the UNIVERSAL BRIDGE - any chat UI (OpenChat, Ollama WebUI,
ChatGPT clones) can use this endpoint.

Model format: "skill:collection:role"
  - "aszf-rag:azhu-test:expert"
  - "aszf-rag:npra-faq:baseline"
  - "process-doc" (no collection/role needed)

Usage:
    POST /v1/chat/completions
    {
        "model": "aszf-rag:azhu-test:expert",
        "messages": [{"role": "user", "content": "Milyen adatokat kezel?"}],
        "stream": false
    }
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


# ---------------------------------------------------------------------------
# /v1/models - Required by Open WebUI and other chat UIs
# ---------------------------------------------------------------------------


@router.get("/models")
async def list_models() -> dict:
    """List available models (OpenAI-compatible format).

    Open WebUI calls this to populate the model selector dropdown.
    Each model maps to a skill:collection:role combination.
    """
    models = [
        {
            "id": "aszf-rag:azhu-test:expert",
            "object": "model",
            "created": 1711670400,
            "owned_by": "aiflow",
            "name": "ASZF RAG Expert (Allianz)",
        },
        {
            "id": "aszf-rag:azhu-test:mentor",
            "object": "model",
            "created": 1711670400,
            "owned_by": "aiflow",
            "name": "ASZF RAG Mentor (Allianz)",
        },
        {
            "id": "aszf-rag:azhu-test:baseline",
            "object": "model",
            "created": 1711670400,
            "owned_by": "aiflow",
            "name": "ASZF RAG Baseline (Allianz)",
        },
        {
            "id": "process-doc",
            "object": "model",
            "created": 1711670400,
            "owned_by": "aiflow",
            "name": "Process Documentation (BPMN)",
        },
        {
            "id": "email-intent:azhu:hybrid",
            "object": "model",
            "created": 1711670400,
            "owned_by": "aiflow",
            "name": "Email Intent (Allianz, Hybrid ML+LLM)",
        },
        {
            "id": "email-intent:azhu:llm-only",
            "object": "model",
            "created": 1711670400,
            "owned_by": "aiflow",
            "name": "Email Intent (Allianz, LLM Only)",
        },
    ]
    return {"object": "list", "data": models}


# ---------------------------------------------------------------------------
# Request / Response models (OpenAI format)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class ChatCompletionRequest(BaseModel):
    model: str = "aszf-rag:default:baseline"
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = ""
    choices: list[ChatCompletionChoice] = Field(default_factory=list)
    usage: UsageInfo = Field(default_factory=UsageInfo)


# ---------------------------------------------------------------------------
# Model string parser
# ---------------------------------------------------------------------------


def _parse_model(model_str: str) -> tuple[str, str, str]:
    """Parse model string into (skill, collection, role).

    Examples:
        "aszf-rag:azhu-test:expert" -> ("aszf-rag", "azhu-test", "expert")
        "aszf-rag:azhu-test"        -> ("aszf-rag", "azhu-test", "baseline")
        "aszf-rag"                  -> ("aszf-rag", "default", "baseline")
        "process-doc"               -> ("process-doc", "", "")
    """
    parts = model_str.split(":")
    skill = parts[0] if len(parts) >= 1 else "aszf-rag"
    collection = parts[1] if len(parts) >= 2 else "default"
    role = parts[2] if len(parts) >= 3 else "baseline"
    return skill, collection, role


# ---------------------------------------------------------------------------
# Skill dispatchers
# ---------------------------------------------------------------------------


async def _run_aszf_rag(
    question: str,
    collection: str,
    role: str,
    history: list[dict[str, str]],
) -> dict[str, Any]:
    """Run the ASZF RAG query pipeline."""
    from skills.aszf_rag_chat.workflows.query import (
        build_context,
        detect_hallucination,
        extract_citations,
        generate_answer,
        rewrite_query,
        search_documents,
    )

    data: dict[str, Any] = {
        "question": question,
        "collection": collection,
        "role": role,
        "language": "hu",
        "conversation_history": history,
        "top_k": 5,
    }

    r1 = await rewrite_query(data)
    r2 = await search_documents({**data, **r1})
    r3 = await build_context({**data, **r2})
    r4 = await generate_answer({**data, **r3})
    r5 = await extract_citations(r4)
    r6 = await detect_hallucination(r5)

    return r6


async def _run_process_doc(question: str) -> dict[str, Any]:
    """Run the Process Documentation pipeline."""
    from skills.process_documentation.workflow import (
        classify_intent,
        elaborate,
        extract,
        generate_diagram,
        review,
    )

    data = {"user_input": question}
    r1 = await classify_intent(data)
    if r1.get("category") != "process":
        return {"answer": f"Ez nem uzleti folyamat leiras. (category: {r1.get('category')})"}

    r2 = await elaborate({**r1, "user_input": question})
    r3 = await extract(r2)
    r4 = await review({**r3, "original_input": question})
    r5 = await generate_diagram(r3)

    return {
        "answer": f"**{r5.get('title', 'Diagram')}**\n\n```mermaid\n{r5.get('mermaid_code', '')}\n```\n\n"
        f"Review: {r4.get('review', {}).get('score', '?')}/10",
    }


async def _run_email_intent(
    text: str,
    collection: str,
    role: str,
) -> dict[str, Any]:
    """Run the Email Intent Processor pipeline."""
    from skills.email_intent_processor.workflows.classify import (
        classify_intent,
        decide_routing,
        extract_entities,
        parse_email,
        process_attachments,
        score_priority,
    )

    data: dict[str, Any] = {
        "source": text,
        "subject": "",
        "body": text,
        "sender": "",
        "customer": collection,
        "classification_strategy": role if role != "baseline" else "hybrid",
    }

    r1 = await parse_email(data)
    r2 = await process_attachments(r1)
    r3 = await classify_intent(r2)
    r4 = await extract_entities(r3)
    r5 = await score_priority(r4)
    r6 = await decide_routing(r5)

    intent = r3.get("primary_intent", "unknown")
    confidence = r3.get("intent_confidence", 0.0)
    entities = r4.get("extracted_entities", [])
    priority = r5.get("priority", 3)
    queue = r6.get("routed_to", "")
    department = r6.get("department", "")

    answer = "**Email feldolgozas eredmenye:**\n\n"
    answer += f"- **Intent:** {intent} (confidence: {confidence:.0%})\n"
    answer += f"- **Prioritas:** {priority}/5\n"
    answer += f"- **Routing:** {department} / {queue}\n"
    if entities:
        answer += "\n**Kinyert adatpontok:**\n"
        for e in entities[:5]:
            answer += f"- {e.get('type', '?')}: {e.get('value', '?')}\n"

    return {"answer": answer}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """OpenAI-compatible chat completions endpoint.

    Routes to the appropriate skill based on the model string.
    """
    skill, collection, role = _parse_model(request.model)
    question = request.messages[-1].content if request.messages else ""
    history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]

    logger.info(
        "chat_completion_request",
        skill=skill,
        collection=collection,
        role=role,
        question_len=len(question),
    )

    start = time.monotonic()

    try:
        if skill in ("aszf-rag", "aszf_rag_chat"):
            result = await _run_aszf_rag(question, collection, role, history)
        elif skill in ("process-doc", "process_documentation"):
            result = await _run_process_doc(question)
        elif skill in ("email-intent", "email_intent_processor"):
            result = await _run_email_intent(question, collection, role)
        else:
            raise HTTPException(404, f"Unknown skill: {skill}")

        answer = result.get("answer", "Nincs valasz.")
        duration = (time.monotonic() - start) * 1000

        logger.info(
            "chat_completion_done",
            skill=skill,
            answer_len=len(answer),
            duration_ms=round(duration),
        )

        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role="assistant", content=answer),
                )
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_completion_error", skill=skill, error=str(e))
        raise HTTPException(500, f"Skill error: {e}") from e
