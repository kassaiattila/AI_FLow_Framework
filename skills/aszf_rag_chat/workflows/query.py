"""RAG query workflow - rewrite, search, answer, cite, verify.

Pipeline: rewrite_query -> search_documents -> build_context
       -> generate_answer -> extract_citations -> detect_hallucination

Answers user questions by retrieving relevant ASZF document chunks
via hybrid search and generating grounded, cited responses.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import asyncpg
import structlog
from skills.aszf_rag_chat.models import Citation, RoleType

from aiflow.core.config import get_settings
from aiflow.engine.step import step
from aiflow.engine.workflow import WorkflowBuilder, workflow
from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager
from aiflow.prompts.schema import PromptDefinition
from aiflow.prompts.workflow import PromptWorkflow
from aiflow.prompts.workflow_executor import PromptWorkflowExecutor
from aiflow.prompts.workflow_loader import PromptWorkflowLoader
from aiflow.vectorstore.embedder import Embedder
from aiflow.vectorstore.pgvector_store import PgVectorStore
from aiflow.vectorstore.search import HybridSearchEngine, SearchConfig

# Sprint T / S150 (S141-FU-3): the workflow descriptor name + skill key the
# executor uses for opt-in resolution. Module-level constants so tests can
# reference them without recreating the executor.
WORKFLOW_NAME = "aszf_rag_chain"
SKILL_NAME = "aszf_rag_chat"
BASELINE_PERSONA = "baseline"


__all__ = [
    "rewrite_query",
    "search_documents",
    "build_context",
    "generate_answer",
    "extract_citations",
    "detect_hallucination",
    "log_query",
    "aszf_rag_query",
]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level services (closure pattern)
# ---------------------------------------------------------------------------

_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
_model_client = ModelClient(generation_backend=_backend, embedding_backend=_backend)

# Sprint T / S150 (S141-FU-3): when AIFLOW_PROMPT_WORKFLOWS__ENABLED=true the
# local _prompt_manager is built workflow-aware so PromptWorkflowExecutor
# can resolve aszf_rag_chain. Flag-off keeps the manager in legacy mode and
# every existing call site is byte-stable.
_wf_settings = get_settings().prompt_workflows
_workflow_loader: PromptWorkflowLoader | None = None
if _wf_settings.enabled:
    _wf_dir = Path(_wf_settings.workflows_dir)
    if not _wf_dir.is_absolute():
        # Repo root = four parents up from this file
        # (skills/<name>/workflows/query.py).
        _wf_dir = Path(__file__).resolve().parents[3] / _wf_dir
    _workflow_loader = PromptWorkflowLoader(_wf_dir)
    _workflow_loader.register_dir()

_prompt_manager = PromptManager(
    workflows_enabled=_wf_settings.enabled,
    workflow_loader=_workflow_loader,
)
_prompt_manager.register_yaml_dir(Path(__file__).parent.parent / "prompts")

# Sprint T / S150 — PromptWorkflow opt-in shim. Resolution-only; flag-off
# default returns ``None`` and the legacy single-prompt path runs unchanged.
prompt_workflow_executor = PromptWorkflowExecutor(
    manager=_prompt_manager,
    settings=_wf_settings,
)


def _resolve_workflow_for_persona(
    role: str,
) -> tuple[PromptWorkflow, dict[str, PromptDefinition]] | None:
    """Resolve ``aszf_rag_chain`` for the baseline persona only.

    Expert / mentor personas keep the legacy single-prompt path on every
    flag state (out of scope per Sprint T plan §6 R3). Returns ``None``
    when:

    * ``role`` is not ``BASELINE_PERSONA``;
    * the workflow shim is off for this skill (flag-off or skill not in CSV);
    * the descriptor / nested prompts cannot be resolved.

    Callers fall back to the legacy ``_prompt_manager.get(...)`` path on
    a ``None`` return.
    """
    if role != BASELINE_PERSONA:
        return None
    return prompt_workflow_executor.resolve_for_skill(SKILL_NAME, WORKFLOW_NAME)


import os as _os

_db_url = _os.getenv(
    "AIFLOW_DATABASE_URL", "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev"
)
_vector_store = PgVectorStore(database_url=_db_url, table_name="rag_chunks")
_embedder = Embedder(
    _model_client,
    default_model="openai/text-embedding-3-small",
    batch_size=5,
    max_chars=6000,
)

_search_config = SearchConfig(
    vector_weight=0.6,
    keyword_weight=0.4,
    top_k=5,
    similarity_threshold=0.0,  # Disabled - filtering done by top_k ordering instead
    rrf_k=60,
)
_search_engine = HybridSearchEngine.from_config(_vector_store, _search_config)

# ---------------------------------------------------------------------------
# Role -> prompt mapping
# ---------------------------------------------------------------------------

_ROLE_PROMPT_MAP = {
    RoleType.BASELINE: "aszf-rag/system_prompt_baseline",
    RoleType.MENTOR: "aszf-rag/system_prompt_mentor",
    RoleType.EXPERT: "aszf-rag/system_prompt_expert",
}


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@step(name="rewrite_query", description="Expand query with Hungarian legal terms")
async def rewrite_query(data: dict) -> dict:
    """Rewrite user question for optimal retrieval.

    Expands abbreviations, adds Hungarian legal synonyms, and reformulates
    the question for better vector + keyword search recall.

    Input:
        question: str - original user question
        language: str - document language (default: "hu")

    Output:
        rewritten_query: str
        original_question: str
    """
    question = data.get("question", "")
    language = data.get("language", "hu")
    role = data.get("role", RoleType.BASELINE)

    if not question.strip():
        raise ValueError("Question cannot be empty")

    # Sprint T / S150 — baseline persona resolves rewrite_query through the
    # aszf_rag_chain workflow when the shim is on; every other persona keeps
    # the legacy lookup path byte-stable.
    resolved = _resolve_workflow_for_persona(role)
    if resolved is not None:
        _, prompt_map = resolved
        prompt = prompt_map.get("rewrite_query") or _prompt_manager.get("aszf-rag/query_rewriter")
    else:
        prompt = _prompt_manager.get("aszf-rag/query_rewriter")
    messages = prompt.compile(
        variables={
            "question": question,
            "language": language,
        }
    )

    result = await _model_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
    )

    rewritten = result.output.text.strip()
    logger.info(
        "rewrite_query.done",
        original_len=len(question),
        rewritten_len=len(rewritten),
    )
    return {
        "rewritten_query": rewritten,
        "original_question": question,
    }


@step(name="search_documents", description="Hybrid search for relevant chunks")
async def search_documents(data: dict) -> dict:
    """Execute hybrid search (vector + BM25 + RRF) for relevant chunks.

    Embeds the rewritten query and searches via HybridSearchEngine.

    Input:
        rewritten_query: str - from rewrite_query
        original_question: str
        collection: str (optional, default: "default")
        top_k: int (optional, default: 5)

    Output:
        search_results: list[dict] - SearchResult dicts
        query: str - the rewritten query used
        original_question: str
        collection: str
    """
    rewritten_query = data.get("rewritten_query", data.get("question", ""))
    original_question = data.get("original_question", rewritten_query)
    collection = data.get("collection", "default")
    top_k = data.get("top_k", 5)
    skill_name = "aszf_rag_chat"

    # Embed the rewritten query
    query_embeddings = await _embedder.embed_texts([rewritten_query])
    query_embedding = query_embeddings[0] if query_embeddings else []

    # Execute hybrid search
    results = await _search_engine.search(
        collection=collection,
        skill_name=skill_name,
        query_embedding=query_embedding,
        query_text=rewritten_query,
        top_k=top_k,
    )

    # Convert to serializable dicts
    search_results = [
        {
            "chunk_id": str(r.chunk_id),
            "content": r.content,
            "score": r.score,
            "vector_score": r.vector_score,
            "keyword_score": r.keyword_score,
            "document_title": r.document_title or "",
            "section_title": r.section_title or "",
            "page_start": r.page_start,
            "metadata": r.metadata,
        }
        for r in results
    ]

    logger.info(
        "search_documents.done",
        query_len=len(rewritten_query),
        results=len(search_results),
        top_score=search_results[0]["score"] if search_results else 0.0,
        collection=collection,
    )
    return {
        "search_results": search_results,
        "query": rewritten_query,
        "original_question": original_question,
        "collection": collection,
    }


@step(name="build_context", description="Build context from search results")
async def build_context(data: dict) -> dict:
    """Build numbered context string from search results.

    Concatenates top-K chunks in a numbered format:
    [1] Source: document_name
    Content: chunk text...

    Input:
        search_results: list[dict] - from search_documents
        original_question: str

    Output:
        context: str - formatted context string
        sources: list[dict] - source metadata for citation
        question: str - original question
        search_results: list[dict] - pass through
    """
    search_results = data.get("search_results", [])
    question = data.get("original_question", data.get("question", ""))

    if not search_results:
        logger.warning("build_context.no_results")
        return {
            "context": "",
            "sources": [],
            "question": question,
            "search_results": search_results,
        }

    context_parts: list[str] = []
    sources: list[dict[str, Any]] = []

    for idx, result in enumerate(search_results, 1):
        doc_name = result.get("document_title", "Unknown")
        section = result.get("section_title", "")
        content = result.get("content", "")
        score = result.get("score", 0.0)
        page = result.get("page_start")
        chunk_meta = result.get("metadata", {})

        # Build numbered context entry
        source_line = f"[{idx}] Source: {doc_name}"
        if section:
            source_line += f" / {section}"
        if page is not None:
            source_line += f" (p. {page})"

        context_parts.append(f"{source_line}\nContent: {content}")

        sources.append(
            {
                "index": idx,
                "document_name": doc_name,
                "section": section,
                "page": page,
                "chunk_index": chunk_meta.get("chunk_index", 0),
                "relevance_score": score,
                "excerpt": content[:200] if content else "",
            }
        )

    context = "\n\n".join(context_parts)

    logger.info(
        "build_context.done",
        sources=len(sources),
        context_chars=len(context),
    )
    return {
        "context": context,
        "sources": sources,
        "question": question,
        "search_results": search_results,
    }


@step(name="generate_answer", description="LLM answer generation with role-based prompt")
async def generate_answer(data: dict) -> dict:
    """Generate answer grounded in retrieved context.

    Loads role-based system prompt (baseline/mentor/expert) and generates
    a response using the context from search results.

    Input:
        context: str - from build_context
        question: str
        sources: list[dict]
        search_results: list[dict]
        role: str (optional, default: "baseline")
        conversation_history: list[dict] (optional)

    Output:
        answer: str
        context: str
        sources: list[dict]
        search_results: list[dict]
        role: str
    """
    context = data.get("context", "")
    question = data.get("question", "")
    sources = data.get("sources", [])
    search_results = data.get("search_results", [])
    role = data.get("role", RoleType.BASELINE)
    conversation_history = data.get("conversation_history", [])

    # Load role-specific system prompt. Sprint T / S150 — baseline persona
    # may resolve system_baseline through the aszf_rag_chain workflow when
    # the shim is on; expert/mentor stay on the legacy single-prompt path.
    prompt_name = _ROLE_PROMPT_MAP.get(role, _ROLE_PROMPT_MAP[RoleType.BASELINE])
    try:
        resolved = _resolve_workflow_for_persona(role)
        if resolved is not None:
            _, prompt_map = resolved
            system_prompt = prompt_map.get("system_baseline") or _prompt_manager.get(prompt_name)
        else:
            system_prompt = _prompt_manager.get(prompt_name)
        system_messages = system_prompt.compile(
            variables={
                "context": context,
                "question": question,
                "company_name": data.get("company_name", "Allianz Hungaria Zrt."),
                "history": str(conversation_history[-6:]) if conversation_history else "",
            }
        )
        # Ensure the context + question are in a user message
        # (role prompts may only have system: without user:)
        has_user_msg = any(m.get("role") == "user" for m in system_messages)
        if not has_user_msg:
            system_messages.append(
                {
                    "role": "user",
                    "content": f"Kontextus a dokumentumokbol:\n\n{context}\n\n---\nKerdes: {question}",
                }
            )
    except Exception as exc:
        logger.warning(
            "generate_answer.prompt_fallback",
            role=role,
            error=str(exc),
        )
        # Fallback system message if prompt not found
        system_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert assistant answering questions about insurance "
                    "terms and conditions (ASZF). Answer ONLY based on the provided "
                    "context. If the answer is not in the context, say so clearly. "
                    "Cite sources using [N] notation.\n\n"
                    f"Context:\n{context}"
                ),
            },
            {
                "role": "user",
                "content": f"Kontextus a dokumentumokbol:\n\n{context}\n\n---\nKerdes: {question}",
            },
        ]

    # Inject conversation history before the final user message
    if conversation_history:
        # Insert history messages before the last user message
        history_messages = []
        for msg in conversation_history:
            history_messages.append(
                {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                }
            )
        # system + history + user
        if len(system_messages) >= 2:
            system_messages = [system_messages[0]] + history_messages + system_messages[1:]

    start_ms = time.monotonic() * 1000

    result = await _model_client.generate(
        messages=system_messages,
        model="openai/gpt-4o",
        temperature=0.3,
        max_tokens=2000,
    )

    latency_ms = time.monotonic() * 1000 - start_ms
    answer = result.output.text.strip()

    logger.info(
        "generate_answer.done",
        role=role,
        answer_len=len(answer),
        latency_ms=round(latency_ms, 1),
        cost_usd=result.cost_usd,
    )
    return {
        "answer": answer,
        "context": context,
        "sources": sources,
        "search_results": search_results,
        "role": role,
    }


@step(name="extract_citations", description="Extract citations from answer")
async def extract_citations(data: dict) -> dict:
    """Extract and validate citations from the generated answer.

    Uses PromptManager prompt "aszf-rag/citation_extractor" to identify
    which source references [N] appear in the answer and map them to
    actual source documents.

    Input:
        answer: str - from generate_answer
        context: str
        sources: list[dict]
        search_results: list[dict]

    Output:
        answer: str
        citations: list[dict] - Citation model dicts
        sources: list[dict]
        search_results: list[dict]
    """
    answer = data.get("answer", "")
    context = data.get("context", "")
    sources = data.get("sources", [])
    search_results = data.get("search_results", [])
    role = data.get("role", RoleType.BASELINE)

    # Sprint T / S150 — baseline persona resolves extract_citations through
    # the aszf_rag_chain workflow when the shim is on; expert/mentor stay on
    # the legacy lookup path.
    resolved = _resolve_workflow_for_persona(role)
    if resolved is not None:
        _, prompt_map = resolved
        prompt = prompt_map.get("extract_citations") or _prompt_manager.get(
            "aszf-rag/citation_extractor"
        )
    else:
        prompt = _prompt_manager.get("aszf-rag/citation_extractor")
    messages = prompt.compile(
        variables={
            "answer": answer,
            "context": context,
            "sources": str(sources),
        }
    )

    result = await _model_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
        response_model=list[Citation],
    )

    citations_raw = result.output.structured
    # Convert Citation objects to dicts
    if isinstance(citations_raw, list):
        citations = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else c for c in citations_raw
        ]
    else:
        citations = []

    logger.info(
        "extract_citations.done",
        citation_count=len(citations),
    )
    return {
        "answer": answer,
        "citations": citations,
        "sources": sources,
        "search_results": search_results,
    }


@step(name="detect_hallucination", description="Verify answer grounding")
async def detect_hallucination(data: dict) -> dict:
    """Detect hallucination by verifying answer is grounded in context.

    Uses PromptManager prompt "aszf-rag/hallucination_detector" to score
    how well the answer is supported by the retrieved context.
    Score: 1.0 = fully grounded, 0.0 = fully hallucinated.

    Input:
        answer: str
        citations: list[dict]
        sources: list[dict]
        search_results: list[dict]

    Output:
        answer: str
        citations: list[Citation dict]
        search_results: list[SearchResult dict]
        hallucination_score: float (0.0 - 1.0)
        processing_time_ms: float
        tokens_used: int
        cost_usd: float
    """
    answer = data.get("answer", "")
    citations = data.get("citations", [])
    search_results = data.get("search_results", [])

    # Reconstruct context from sources for verification
    context_for_check = "\n\n".join(r.get("content", "") for r in search_results)

    prompt = _prompt_manager.get("aszf-rag/hallucination_detector")
    messages = prompt.compile(
        variables={
            "answer": answer,
            "context": context_for_check,
        }
    )

    result = await _model_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
    )

    # Parse score from response. Accept three formats:
    #   1. Strict JSON dict: {"score": float, "claims": [...], "hallucinated_claims": [...]}
    #   2. Bare JSON scalar: 0.85  (legacy prompt returned a float)
    #   3. Plain text float: "0.85 some explanation"  (final fallback)
    score_text = result.output.text.strip()
    hallucinated_claims: list[str] = []
    try:
        payload = json.loads(score_text)
        if isinstance(payload, dict):
            raw_score = payload.get("score", 0.5)
            hallucinated_claims = payload.get("hallucinated_claims", []) or []
        else:
            # bare JSON scalar (int, float, bool)
            raw_score = payload
        hallucination_score = max(0.0, min(1.0, float(raw_score)))
    except (json.JSONDecodeError, TypeError, ValueError):
        # Legacy fallback: bare float as first token in plain text
        try:
            hallucination_score = float(score_text.split()[0])
            hallucination_score = max(0.0, min(1.0, hallucination_score))
        except (ValueError, IndexError):
            logger.warning(
                "detect_hallucination.parse_error",
                raw=score_text[:100],
            )
            hallucination_score = 0.5

    logger.info(
        "detect_hallucination.done",
        score=hallucination_score,
        grounded=hallucination_score >= 0.9,
        unsupported_claim_count=len(hallucinated_claims),
    )

    # Build final QueryOutput-compatible dict
    return {
        "answer": answer,
        "citations": citations,
        "search_results": search_results,
        "hallucination_score": hallucination_score,
        "hallucinated_claims": hallucinated_claims,
        "processing_time_ms": 0.0,  # filled by runner
        "tokens_used": 0,
        "cost_usd": result.cost_usd,
    }


# ---------------------------------------------------------------------------
# Query logging helper
# ---------------------------------------------------------------------------


async def _log_query_to_db(data: dict[str, Any]) -> None:
    """Persist query data to rag_query_log (best-effort, never raises).

    Connects to PostgreSQL and INSERTs one row. If anything fails the
    error is logged via structlog but the pipeline is NOT affected.
    """
    try:
        conn = await asyncpg.connect(_db_url)
        try:
            await conn.execute(
                """
                INSERT INTO rag_query_log
                    (collection, question, rewritten_query, answer,
                     sources_count, hallucination_score, response_time_ms,
                     cost_usd, role)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                data.get("collection", "default"),
                data.get("question", ""),
                data.get("rewritten_query", ""),
                data.get("answer", ""),
                data.get("sources_count", 0),
                data.get("hallucination_score"),
                data.get("response_time_ms"),
                data.get("cost_usd", 0.0),
                data.get("role", "baseline"),
            )
        finally:
            await conn.close()
        logger.info(
            "log_query_to_db.saved",
            collection=data.get("collection", "default"),
        )
    except Exception as exc:
        logger.warning(
            "log_query_to_db.failed",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Log query step
# ---------------------------------------------------------------------------


@step(name="log_query", description="Persist query analytics to rag_query_log")
async def log_query(data: dict) -> dict:
    """Log the completed query pipeline result to rag_query_log.

    Best-effort: failures are logged but do not break the pipeline.
    Passes all data through unchanged so downstream consumers are unaffected.

    Input:
        answer: str
        citations: list[dict]
        search_results: list[dict]
        hallucination_score: float
        processing_time_ms: float
        tokens_used: int
        cost_usd: float
        (plus any pass-through fields from earlier steps)

    Output:
        Same as input (pass-through).
    """
    await _log_query_to_db(
        {
            "collection": data.get("collection", "default"),
            "question": data.get("question", data.get("original_question", "")),
            "rewritten_query": data.get("rewritten_query", ""),
            "answer": data.get("answer", ""),
            "sources_count": len(data.get("search_results", [])),
            "hallucination_score": data.get("hallucination_score"),
            "response_time_ms": data.get("processing_time_ms"),
            "cost_usd": data.get("cost_usd", 0.0),
            "role": data.get("role", "baseline"),
        }
    )
    return data


# ---------------------------------------------------------------------------
# Workflow registration
# ---------------------------------------------------------------------------


@workflow(name="aszf-rag-query", version="1.0.0", skill="aszf_rag_chat")
def aszf_rag_query(wf: WorkflowBuilder) -> None:
    """RAG query pipeline: rewrite -> search -> context -> answer -> cite -> verify -> log."""
    wf.step(rewrite_query)
    wf.step(search_documents, depends_on=["rewrite_query"])
    wf.step(build_context, depends_on=["search_documents"])
    wf.step(generate_answer, depends_on=["build_context"])
    wf.step(extract_citations, depends_on=["generate_answer"])
    wf.step(detect_hallucination, depends_on=["extract_citations"])
    wf.step(log_query, depends_on=["detect_hallucination"])
