"""Email processing result endpoints + upload/process."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/emails", tags=["emails"])

ALLOWED_EXTENSIONS = {".eml", ".msg", ".txt"}


class EmailResultItem(BaseModel):
    """Email processing result summary."""
    email_id: str
    subject: str
    sender: str
    received_date: str | None = None
    intent_id: str | None = None
    intent_display_name: str | None = None
    intent_confidence: float = 0.0
    intent_method: str | None = None
    priority_level: int | None = None
    department_name: str | None = None
    queue_name: str | None = None
    entity_count: int = 0
    attachment_count: int = 0
    processing_time_ms: float = 0.0
    status: str = "completed"


class EmailListResponse(BaseModel):
    """List of email processing results."""
    emails: list[EmailResultItem]
    total: int


def _get_db_url() -> str:
    return os.getenv(
        "AIFLOW_DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )


@router.get("", response_model=EmailListResponse)
async def list_emails(
    intent: str | None = Query(None, description="Filter by intent_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EmailListResponse:
    """List email processing results.

    Queries workflow_runs where skill_name='email_intent_processor'
    and extracts result data from output_data JSONB.
    """
    emails: list[EmailResultItem] = []
    total = 0

    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
            where = "WHERE r.skill_name = 'email_intent_processor' AND r.status = 'completed'"
            params: list[Any] = []
            idx = 1

            if intent:
                where += f" AND r.output_data->>'intent_id' = ${idx}"
                params.append(intent)
                idx += 1

            count_row = await conn.fetchrow(
                f"SELECT COUNT(*) AS cnt FROM workflow_runs r {where}",
                *params,
            )
            total = count_row["cnt"] if count_row else 0

            params.extend([limit, offset])
            rows = await conn.fetch(
                f"""
                SELECT r.id, r.output_data, r.started_at, r.total_duration_ms
                FROM workflow_runs r
                {where}
                ORDER BY r.started_at DESC NULLS LAST
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params,
            )

            for row in rows:
                data = row["output_data"] or {}
                intent_data = data.get("intent") or {}
                priority_data = data.get("priority") or {}
                routing_data = data.get("routing") or {}
                entities_data = data.get("entities") or {}

                emails.append(EmailResultItem(
                    email_id=data.get("email_id", str(row["id"])),
                    subject=data.get("subject", ""),
                    sender=data.get("sender", ""),
                    received_date=row["started_at"].isoformat() if row["started_at"] else None,
                    intent_id=intent_data.get("intent_id"),
                    intent_display_name=intent_data.get("intent_display_name"),
                    intent_confidence=intent_data.get("confidence", 0.0),
                    intent_method=intent_data.get("method"),
                    priority_level=priority_data.get("priority_level"),
                    department_name=routing_data.get("department_name"),
                    queue_name=routing_data.get("queue_name"),
                    entity_count=entities_data.get("entity_count", 0),
                    attachment_count=data.get("attachment_count", 0),
                    processing_time_ms=row["total_duration_ms"] or 0.0,
                ))
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("emails_db_failed", error=str(e))

    # Fallback to JSON file if DB is empty
    if not emails:
        import json as _json
        for base in [Path("aiflow-ui/data"), Path("aiflow-ui/public/data")]:
            f = base / "emails.json"
            if f.exists():
                try:
                    raw = _json.loads(f.read_text(encoding="utf-8"))
                    items = raw if isinstance(raw, list) else raw.get("emails", [])
                    for item in items:
                        emails.append(EmailResultItem(
                            email_id=item.get("email_id", ""),
                            subject=item.get("subject", ""),
                            sender=item.get("sender", ""),
                            received_date=item.get("received_date"),
                            intent_id=item.get("intent", {}).get("intent_id") if isinstance(item.get("intent"), dict) else None,
                            intent_display_name=item.get("intent", {}).get("intent_display_name") if isinstance(item.get("intent"), dict) else None,
                            intent_confidence=item.get("intent", {}).get("confidence", 0) if isinstance(item.get("intent"), dict) else 0,
                            intent_method=item.get("intent", {}).get("method") if isinstance(item.get("intent"), dict) else None,
                            priority_level=item.get("priority", {}).get("priority_level") if isinstance(item.get("priority"), dict) else None,
                            department_name=item.get("routing", {}).get("department_name") if isinstance(item.get("routing"), dict) else None,
                            queue_name=item.get("routing", {}).get("queue_name") if isinstance(item.get("routing"), dict) else None,
                            attachment_count=len(item.get("attachment_summaries", [])),
                        ))
                    if emails:
                        return EmailListResponse(emails=emails, total=len(emails))
                except Exception:
                    pass
                break

    return EmailListResponse(emails=emails, total=total)


# ---------------------------------------------------------------------------
# Upload & Process
# ---------------------------------------------------------------------------

def _email_upload_dir() -> Path:
    d = Path(os.getenv("AIFLOW_EMAIL_UPLOAD_DIR", "./data/uploads/emails"))
    d.mkdir(parents=True, exist_ok=True)
    return d


class EmailUploadResponse(BaseModel):
    uploaded: int = 0
    files: list[str] = []
    errors: list[str] = []


class EmailProcessRequest(BaseModel):
    file: str


class EmailProcessResponse(BaseModel):
    file: str
    source: str = "backend"
    intent: dict[str, Any] | None = None
    entities: dict[str, Any] | None = None
    priority: dict[str, Any] | None = None
    routing: dict[str, Any] | None = None
    error: str | None = None


@router.post("/upload", response_model=EmailUploadResponse)
async def upload_emails(files: list[UploadFile] = File(...)) -> EmailUploadResponse:
    """Upload email files (.eml, .msg, .txt) for processing."""
    upload_dir = _email_upload_dir()
    uploaded: list[str] = []
    errors: list[str] = []

    for f in files:
        if not f.filename:
            continue
        name = Path(f.filename).name  # safe basename
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{name}: Invalid extension {ext}")
            continue
        content = await f.read()
        (upload_dir / name).write_bytes(content)
        uploaded.append(name)
        logger.info("email_uploaded", filename=name, size=len(content))

    return EmailUploadResponse(uploaded=len(uploaded), files=uploaded, errors=errors)


@router.post("/process", response_model=EmailProcessResponse)
async def process_email(request: EmailProcessRequest) -> EmailProcessResponse:
    """Process an uploaded email using the email_intent_processor skill in-process."""
    upload_dir = _email_upload_dir()
    file_path = upload_dir / request.file

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file}")

    try:
        from skills.email_intent_processor.workflows.pipeline import (
            parse_email,
            classify_intent,
            extract_entities,
            determine_priority,
            route_email,
        )
    except ImportError as e:
        logger.error("email_skill_import_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Email processor skill not available: {e}")

    output_dir = Path(tempfile.mkdtemp(prefix="aiflow_email_"))
    try:
        data: dict[str, Any] = {
            "input_file": str(file_path),
            "output_dir": str(output_dir),
        }
        data = await parse_email(data)
        data = await classify_intent(data)
        data = await extract_entities(data)
        data = await determine_priority(data)
        data = await route_email(data)
    except Exception as e:
        logger.error("process_email_failed", error=str(e))
        return EmailProcessResponse(file=request.file, source="backend", error=str(e))

    return EmailProcessResponse(
        file=request.file,
        source="backend",
        intent=data.get("intent"),
        entities=data.get("entities"),
        priority=data.get("priority"),
        routing=data.get("routing"),
    )
