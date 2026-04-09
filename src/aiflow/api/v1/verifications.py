"""Verification Edits API — CRUD for per-field edit diffs + approve/reject workflow.

B7: Verification Page v2 — stores field-level edits with audit trail.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aiflow.api.deps import get_pool

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["verifications"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class VerificationEditCreate(BaseModel):
    field_name: str
    field_category: str | None = None
    original_value: str | None = None
    edited_value: str | None = None
    confidence_score: float | None = None
    comment: str | None = None


class VerificationEdit(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_category: str | None = None
    original_value: str | None = None
    edited_value: str | None = None
    confidence_score: float | None = None
    editor_user_id: str | None = None
    status: str = "pending"
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SaveEditsRequest(BaseModel):
    edits: list[VerificationEditCreate]
    editor_user_id: str | None = None


class VerificationEditResponse(BaseModel):
    edits: list[VerificationEdit]
    total: int
    document_id: str
    source: str = "backend"


class ApproveRejectRequest(BaseModel):
    reviewer_id: str | None = None
    comment: str | None = None


class ApproveRejectResponse(BaseModel):
    count: int
    document_id: str
    status: str
    source: str = "backend"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _row_to_edit(row: dict) -> VerificationEdit:
    """Convert an asyncpg Record (as dict) to VerificationEdit."""
    return VerificationEdit(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        field_name=row["field_name"],
        field_category=row.get("field_category"),
        original_value=row.get("original_value"),
        edited_value=row.get("edited_value"),
        confidence_score=row.get("confidence_score"),
        editor_user_id=row.get("editor_user_id"),
        status=row.get("status", "pending"),
        comment=row.get("comment"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/documents/{document_id}/verifications",
    response_model=VerificationEditResponse,
)
async def save_verification_edits(
    document_id: str,
    request: SaveEditsRequest,
) -> VerificationEditResponse:
    """Batch save verification edits — replaces existing pending edits."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Delete existing pending edits for this document (UPSERT logic)
        await conn.execute(
            "DELETE FROM verification_edits WHERE document_id = $1 AND status = 'pending'",
            document_id,
        )

        inserted: list[VerificationEdit] = []
        now = datetime.now(UTC)
        for edit in request.edits:
            edit_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO verification_edits
                   (id, document_id, field_name, field_category, original_value,
                    edited_value, confidence_score, editor_user_id, status, comment,
                    created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9, $10, $10)""",
                edit_id,
                document_id,
                edit.field_name,
                edit.field_category,
                edit.original_value,
                edit.edited_value,
                edit.confidence_score,
                request.editor_user_id,
                edit.comment,
                now,
            )
            inserted.append(
                VerificationEdit(
                    id=edit_id,
                    document_id=document_id,
                    field_name=edit.field_name,
                    field_category=edit.field_category,
                    original_value=edit.original_value,
                    edited_value=edit.edited_value,
                    confidence_score=edit.confidence_score,
                    editor_user_id=request.editor_user_id,
                    status="pending",
                    comment=edit.comment,
                    created_at=now,
                    updated_at=now,
                )
            )

    logger.info(
        "verification_edits_saved",
        document_id=document_id,
        count=len(inserted),
    )
    return VerificationEditResponse(
        edits=inserted,
        total=len(inserted),
        document_id=document_id,
    )


@router.get(
    "/documents/{document_id}/verifications",
    response_model=VerificationEditResponse,
)
async def get_verification_edits(
    document_id: str,
    status: str | None = Query(None),
    field_name: str | None = Query(None),
) -> VerificationEditResponse:
    """Get all verification edits for a document, optionally filtered."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM verification_edits WHERE document_id = $1"
        params: list = [document_id]
        idx = 2

        if status:
            query += f" AND status = ${idx}"
            params.append(status)
            idx += 1
        if field_name:
            query += f" AND field_name = ${idx}"
            params.append(field_name)
            idx += 1

        query += " ORDER BY created_at ASC"
        rows = await conn.fetch(query, *params)

    edits = [_row_to_edit(dict(r)) for r in rows]
    return VerificationEditResponse(
        edits=edits,
        total=len(edits),
        document_id=document_id,
    )


@router.patch(
    "/documents/{document_id}/verifications/approve",
    response_model=ApproveRejectResponse,
)
async def approve_verification_edits(
    document_id: str,
    request: ApproveRejectRequest,
) -> ApproveRejectResponse:
    """Approve all pending verification edits for a document."""
    pool = await get_pool()
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE verification_edits
               SET status = 'approved', updated_at = $1, comment = COALESCE($2, comment)
               WHERE document_id = $3 AND status = 'pending'""",
            now,
            request.comment,
            document_id,
        )
        count = int(result.split()[-1])  # "UPDATE N"

    logger.info(
        "verification_edits_approved",
        document_id=document_id,
        count=count,
    )
    return ApproveRejectResponse(
        count=count,
        document_id=document_id,
        status="approved",
    )


@router.patch(
    "/documents/{document_id}/verifications/reject",
    response_model=ApproveRejectResponse,
)
async def reject_verification_edits(
    document_id: str,
    request: ApproveRejectRequest,
) -> ApproveRejectResponse:
    """Reject all pending verification edits — comment is required."""
    if not request.comment:
        raise HTTPException(
            status_code=422,
            detail="Comment is required for rejection",
        )

    pool = await get_pool()
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE verification_edits
               SET status = 'rejected', updated_at = $1, comment = $2
               WHERE document_id = $3 AND status = 'pending'""",
            now,
            request.comment,
            document_id,
        )
        count = int(result.split()[-1])

    logger.info(
        "verification_edits_rejected",
        document_id=document_id,
        count=count,
    )
    return ApproveRejectResponse(
        count=count,
        document_id=document_id,
        status="rejected",
    )


@router.get(
    "/verifications/history",
    response_model=VerificationEditResponse,
)
async def verification_history(
    document_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> VerificationEditResponse:
    """Global audit trail for verification edits."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM verification_edits WHERE 1=1"
        params: list = []
        idx = 1

        if document_id:
            query += f" AND document_id = ${idx}"
            params.append(document_id)
            idx += 1
        if status:
            query += f" AND status = ${idx}"
            params.append(status)
            idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

    edits = [_row_to_edit(dict(r)) for r in rows]
    doc_id = document_id or (edits[0].document_id if edits else "")
    return VerificationEditResponse(
        edits=edits,
        total=len(edits),
        document_id=doc_id,
    )
