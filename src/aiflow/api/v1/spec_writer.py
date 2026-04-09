"""Spec Writer API endpoints — B5.2.

CRUD + write endpoint for the Spec Writer skill. Persists generated specs
to the ``generated_specs`` table (migration 030) and exposes markdown /
JSON export.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/specs", tags=["specs"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class WriteSpecRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    spec_type: Literal["feature", "api", "db", "user_story"] = "feature"
    language: Literal["hu", "en"] = "hu"
    context: str | None = None
    created_by: str | None = None


class SpecResponse(BaseModel):
    id: str
    title: str
    spec_type: str
    language: str
    markdown_content: str
    score: float
    is_acceptable: bool
    sections_count: int
    word_count: int
    requirement: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    created_by: str | None = None
    created_at: str = ""
    updated_at: str = ""
    source: str = "backend"


class SpecListResponse(BaseModel):
    specs: list[SpecResponse]
    total: int
    source: str = "backend"


class DeleteResponse(BaseModel):
    deleted: bool = True
    source: str = "backend"


# ---------------------------------------------------------------------------
# DB helpers — reuse the shared asyncpg pool from aiflow.api.deps so this
# router participates in the same connection lifecycle as the rest of the
# app (one pool per event loop, no double-booking of pool connections).
# ---------------------------------------------------------------------------


async def _get_pool() -> asyncpg.Pool:
    # Delegate to the shared pool factory so this router reuses the same
    # event-loop-bound pool instance as the rest of the app. Keeping the
    # import local makes it survive autoformatter runs that would prune
    # top-level imports it thinks are unused.
    from aiflow.api.deps import get_pool as _shared_pool

    return await _shared_pool()


def _row_to_response(row: dict[str, Any]) -> SpecResponse:
    requirement = row.get("requirement")
    if isinstance(requirement, str):
        try:
            requirement = json.loads(requirement)
        except json.JSONDecodeError:
            requirement = None

    review = row.get("review")
    if isinstance(review, str):
        try:
            review = json.loads(review)
        except json.JSONDecodeError:
            review = None

    return SpecResponse(
        id=row["id"],
        title=row.get("title") or "",
        spec_type=row["spec_type"],
        language=row["language"],
        markdown_content=row.get("markdown_content") or "",
        score=float(row.get("score") or 0.0),
        is_acceptable=bool(row.get("is_acceptable") or False),
        sections_count=int(row.get("sections_count") or 0),
        word_count=int(row.get("word_count") or 0),
        requirement=requirement if isinstance(requirement, dict) else None,
        review=review if isinstance(review, dict) else None,
        created_by=row.get("created_by"),
        created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/write", response_model=SpecResponse)
async def write_spec(request: WriteSpecRequest) -> SpecResponse:
    """Run the Spec Writer workflow end-to-end and persist the result."""
    from skills.spec_writer.models import SpecInput
    from skills.spec_writer.workflows.spec_writing import run_spec_writing

    inp = SpecInput(
        raw_text=request.raw_text,
        spec_type=request.spec_type,
        language=request.language,
        context=request.context,
    )

    try:
        result = await run_spec_writing(inp)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_writer_run_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    spec_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO generated_specs
                (id, input_text, spec_type, language, title, markdown_content,
                 requirement, review, score, is_acceptable, sections_count,
                 word_count, created_by, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10,
                        $11, $12, $13, $14, $14)""",
            spec_id,
            request.raw_text,
            request.spec_type,
            request.language,
            result.draft.title,
            result.final_markdown,
            json.dumps(result.requirement.model_dump()),
            json.dumps(result.review.model_dump()),
            result.review.score,
            result.review.is_acceptable,
            result.draft.sections_count,
            result.draft.word_count,
            request.created_by,
            now,
        )

    logger.info(
        "spec_writer.write.done",
        spec_id=spec_id,
        spec_type=request.spec_type,
        language=request.language,
        score=result.review.score,
        is_acceptable=result.review.is_acceptable,
    )

    return SpecResponse(
        id=spec_id,
        title=result.draft.title,
        spec_type=request.spec_type,
        language=request.language,
        markdown_content=result.final_markdown,
        score=result.review.score,
        is_acceptable=result.review.is_acceptable,
        sections_count=result.draft.sections_count,
        word_count=result.draft.word_count,
        requirement=result.requirement.model_dump(),
        review=result.review.model_dump(),
        created_by=request.created_by,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


@router.get("", response_model=SpecListResponse)
async def list_specs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    spec_type: str | None = Query(None),
) -> SpecListResponse:
    """List persisted specs with optional spec_type filter."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if spec_type:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM generated_specs WHERE spec_type = $1",
                spec_type,
            )
            rows = await conn.fetch(
                "SELECT * FROM generated_specs WHERE spec_type = $1 "
                "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                spec_type,
                limit,
                offset,
            )
        else:
            total = await conn.fetchval("SELECT COUNT(*) FROM generated_specs")
            rows = await conn.fetch(
                "SELECT * FROM generated_specs ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit,
                offset,
            )

    return SpecListResponse(
        specs=[_row_to_response(dict(r)) for r in rows],
        total=int(total or 0),
    )


@router.get("/{spec_id}", response_model=SpecResponse)
async def get_spec(spec_id: str) -> SpecResponse:
    """Fetch a single spec by ID."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM generated_specs WHERE id = $1",
            spec_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Spec not found")
    return _row_to_response(dict(row))


@router.delete("/{spec_id}", response_model=DeleteResponse)
async def delete_spec(spec_id: str) -> DeleteResponse:
    """Delete a spec by ID."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM generated_specs WHERE id = $1",
            spec_id,
        )
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="Spec not found")
    return DeleteResponse()


@router.get("/{spec_id}/export")
async def export_spec(
    spec_id: str,
    fmt: Literal["markdown", "html", "json"] = Query("markdown"),
):
    """Export a spec in the requested format (markdown | html | json)."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM generated_specs WHERE id = $1",
            spec_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = _row_to_response(dict(row))

    if fmt == "markdown":
        return PlainTextResponse(
            content=spec.markdown_content,
            media_type="text/markdown",
        )

    if fmt == "json":
        return JSONResponse(content=spec.model_dump())

    # Minimal HTML wrapper — clients can apply their own stylesheet.
    try:
        import markdown as _md

        body_html = _md.markdown(spec.markdown_content, extensions=["tables", "fenced_code"])
    except Exception:
        # Fallback: just escape + <pre> wrap.
        from html import escape

        body_html = f"<pre>{escape(spec.markdown_content)}</pre>"

    html = (
        f'<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{spec.title}</title></head><body>"
        f"<h1>{spec.title}</h1>{body_html}</body></html>"
    )
    return PlainTextResponse(content=html, media_type="text/html")
