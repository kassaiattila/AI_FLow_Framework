"""Email processing API — list, detail, upload, process, classify, connector config CRUD, fetch."""

from __future__ import annotations

import asyncio
import json as _json
import os
import tempfile
import time as _time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import asyncpg
import structlog
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from aiflow.api.deps import get_engine, get_pool

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/emails", tags=["emails"])

ALLOWED_EXTENSIONS = {".eml", ".msg", ".txt"}

_upload_file_field = File(...)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


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
    source: str = "backend"


class EmailDetailResponse(BaseModel):
    """Full email detail with all processing results."""

    email_id: str
    subject: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    received_date: str | None = None
    body: str = ""
    body_html: str = ""
    intent: dict[str, Any] | None = None
    entities: dict[str, Any] | None = None
    priority: dict[str, Any] | None = None
    routing: dict[str, Any] | None = None
    attachment_summaries: list[dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    status: str = "completed"
    source: str = "backend"


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


class ClassifyRequest(BaseModel):
    """Request to classify a text."""

    text: str
    subject: str = ""
    strategy: str | None = None
    schema_name: str = "email_intent_processor"


class ClassifyResponse(BaseModel):
    """Classification result."""

    label: str = ""
    display_name: str = ""
    confidence: float = 0.0
    method: str = ""
    sub_label: str | None = None
    reasoning: str = ""
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "backend"


class ConnectorConfigCreate(BaseModel):
    """Create a new email connector config."""

    name: str
    provider: str  # imap, o365_graph, gmail
    host: str | None = None
    port: int | None = None
    use_ssl: bool = True
    mailbox: str | None = None
    credentials_encrypted: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    polling_interval_minutes: int = 15
    max_emails_per_fetch: int = 50


class ConnectorConfigUpdate(BaseModel):
    """Update an existing connector config."""

    name: str | None = None
    host: str | None = None
    port: int | None = None
    use_ssl: bool | None = None
    mailbox: str | None = None
    credentials_encrypted: str | None = None
    filters: dict[str, Any] | None = None
    polling_interval_minutes: int | None = None
    max_emails_per_fetch: int | None = None
    is_active: bool | None = None


class ConnectorConfigResponse(BaseModel):
    """Single connector config."""

    id: str
    name: str
    provider: str
    host: str | None = None
    port: int | None = None
    use_ssl: bool = True
    mailbox: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    polling_interval_minutes: int = 15
    max_emails_per_fetch: int = 50
    is_active: bool = True
    last_fetched_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    source: str = "backend"


class FetchRequest(BaseModel):
    """Trigger email fetch from a connector."""

    config_id: str
    limit: int = 50
    since_days: int | None = None


class FetchResponse(BaseModel):
    """Fetch operation result."""

    config_id: str
    total_count: int = 0
    new_count: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    source: str = "backend"


class FetchHistoryItem(BaseModel):
    id: str
    config_id: str
    status: str
    email_count: int = 0
    new_emails: int = 0
    duration_ms: float | None = None
    error: str | None = None
    fetched_at: str | None = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str = ""
    folders: list[str] = Field(default_factory=list)
    source: str = "backend"


class ScanRequest(BaseModel):
    """Trigger EmailSource → IntakePackageSink → Classifier scan."""

    max_items: int = Field(10, ge=1, le=100)
    tenant_id: str = "default"
    schema_labels: list[dict[str, Any]] | None = None
    routing_policy_id: str | None = Field(
        default=None,
        description=(
            "Optional IntentRoutingPolicy YAML id to load from "
            "``$AIFLOW_POLICY_DIR/intent_routing/{id}.yaml``. When set, the "
            "orchestrator maps each classification to a routing action and "
            "persists it under ``output_data.routing_action``."
        ),
    )


class ScanItem(BaseModel):
    """One processed package summary."""

    package_id: str
    label: str
    display_name: str = ""
    confidence: float = 0.0
    method: str = ""


class ScanResponse(BaseModel):
    """Result of a scan-classify run."""

    config_id: str
    processed: int = 0
    items: list[ScanItem] = Field(default_factory=list)
    error: str | None = None
    source: str = "backend"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _email_upload_dir() -> Path:
    d = Path(os.getenv("AIFLOW_EMAIL_UPLOAD_DIR", "./data/uploads/emails"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    """Convert asyncpg Record to dict, serializing datetimes and UUIDs."""
    import json as _json
    import uuid as _uuid

    d: dict[str, Any] = {}
    for key, val in dict(row).items():
        if isinstance(val, (datetime, date)):
            d[key] = val.isoformat()
        elif isinstance(val, _uuid.UUID):
            d[key] = str(val)
        elif isinstance(val, str) and key in ("filters",) and val.startswith("{"):
            try:
                d[key] = _json.loads(val)
            except (ValueError, TypeError):
                d[key] = val
        else:
            d[key] = val
    return d


# ---------------------------------------------------------------------------
# Email List (existing)
# ---------------------------------------------------------------------------


@router.get("", response_model=EmailListResponse)
async def list_emails(
    intent: str | None = Query(None, description="Filter by intent_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EmailListResponse:
    """List email processing results from workflow_runs."""
    emails: list[EmailResultItem] = []
    total = 0

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
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
                raw_od = row["output_data"] or {}
                data = (
                    raw_od
                    if isinstance(raw_od, dict)
                    else (_json.loads(raw_od) if isinstance(raw_od, str) else {})
                )
                intent_data = data.get("intent") or {}
                priority_data = data.get("priority") or {}
                routing_data = data.get("routing") or {}
                entities_data = data.get("entities") or {}

                emails.append(
                    EmailResultItem(
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
                    )
                )
    except Exception as e:
        logger.warning("emails_db_failed", error=str(e))

    # Supplement with fetched .eml files that haven't been processed yet
    try:
        fetched_dir = Path(os.getenv("AIFLOW_EMAIL_DIR", "./data/emails"))
        if fetched_dir.exists():
            # Build set of processed file stems from workflow_runs input_data
            processed_files: set[str] = set()
            try:
                pool2 = await get_pool()
                async with pool2.acquire() as conn2:
                    prows = await conn2.fetch(
                        "SELECT input_data FROM workflow_runs WHERE skill_name='email_intent_processor' AND status='completed'"
                    )
                    for pr in prows:
                        raw_id = pr["input_data"]
                        if isinstance(raw_id, str):
                            try:
                                raw_id = _json.loads(raw_id)
                            except Exception:
                                continue
                        if isinstance(raw_id, dict):
                            fpath = raw_id.get("file", "")
                            if fpath:
                                processed_files.add(Path(fpath).stem)
            except Exception:
                pass

            eml_files = sorted(
                fetched_dir.rglob("*.eml"), key=lambda f: f.stat().st_mtime, reverse=True
            )
            for eml_path in eml_files[:200]:
                if eml_path.stem in processed_files:
                    continue
                try:
                    import email as _email_mod

                    raw = eml_path.read_bytes()
                    msg = _email_mod.message_from_bytes(raw)
                    subj = msg.get("Subject", "")
                    from email.header import decode_header as _dh

                    parts = _dh(subj)
                    subj = "".join(
                        p.decode(enc or "utf-8") if isinstance(p, bytes) else p for p, enc in parts
                    )
                    sender = msg.get("From", "")
                    date_str = msg.get("Date", "")
                    emails.append(
                        EmailResultItem(
                            email_id=eml_path.stem,
                            subject=subj,
                            sender=sender,
                            received_date=date_str[:25] if date_str else None,
                            intent_id=None,
                            intent_display_name="Not processed",
                            intent_confidence=0.0,
                            priority_level=None,
                            attachment_count=sum(
                                1 for p in msg.walk() if p.get_content_disposition() == "attachment"
                            ),
                        )
                    )
                    total += 1
                except Exception:
                    continue
    except Exception as e:
        logger.debug("fetched_eml_scan_failed", error=str(e))

    return EmailListResponse(emails=emails, total=total, source="backend")


# ---------------------------------------------------------------------------
# Upload & Process (existing)
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=EmailUploadResponse)
async def upload_emails(files: list[UploadFile] = _upload_file_field) -> EmailUploadResponse:
    """Upload email files (.eml, .msg, .txt) for processing."""
    upload_dir = _email_upload_dir()
    uploaded: list[str] = []
    errors: list[str] = []

    for f in files:
        if not f.filename:
            continue
        name = Path(f.filename).name
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
        from skills.email_intent_processor.workflows.classify import (
            classify_intent as _classify,
        )
        from skills.email_intent_processor.workflows.classify import (
            decide_routing as _route,
        )
        from skills.email_intent_processor.workflows.classify import (
            extract_entities as _extract,
        )
        from skills.email_intent_processor.workflows.classify import (
            parse_email as _parse,
        )
        from skills.email_intent_processor.workflows.classify import (
            score_priority as _priority,
        )
    except ImportError as e:
        logger.error("email_skill_import_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Email processor skill not available: {e}"
        ) from e

    output_dir = Path(tempfile.mkdtemp(prefix="aiflow_email_"))
    try:
        data: dict[str, Any] = {
            "input_file": str(file_path),
            "raw_eml_path": str(file_path),
            "output_dir": str(output_dir),
        }
        data = await _parse(data)
        data = await _classify(data)
        data = await _extract(data)
        data = await _priority(data)
        data = await _route(data)
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


# ---------------------------------------------------------------------------
# Classify (F2 — new)
# ---------------------------------------------------------------------------


@router.post("/classify", response_model=ClassifyResponse)
async def classify_text(request: ClassifyRequest) -> ClassifyResponse:
    """Classify text using the Classifier service with schema-driven labels."""
    from aiflow.services.classifier import ClassifierConfig, ClassifierService

    try:
        # Load intent schema for labels
        from aiflow.tools.schema_registry import SchemaRegistry

        _skills_dir = Path(__file__).parent.parent.parent.parent.parent / "skills"
        registry = SchemaRegistry(skills_dir=_skills_dir)
        intents_schema = registry.load_schema(request.schema_name, "intents")
        raw_intents = intents_schema.get("intents", [])
        # Merge keywords_hu + keywords_en into 'keywords' for the classifier
        schema_labels = []
        for intent in raw_intents:
            label = dict(intent)
            kw = list(label.get("keywords", []))
            kw.extend(label.get("keywords_hu", []))
            kw.extend(label.get("keywords_en", []))
            label["keywords"] = kw
            schema_labels.append(label)
    except Exception as e:
        logger.warning("schema_load_failed", error=str(e))
        schema_labels = []

    config = ClassifierConfig(
        strategy=request.strategy or "sklearn_first",
    )
    classifier = ClassifierService(config=config)
    await classifier.start()

    try:
        result = await classifier.classify(
            text=request.text,
            subject=request.subject,
            schema_labels=schema_labels,
            strategy=request.strategy,
        )
        return ClassifyResponse(
            label=result.label,
            display_name=result.display_name,
            confidence=result.confidence,
            method=result.method,
            sub_label=result.sub_label,
            reasoning=result.reasoning,
            alternatives=result.alternatives,
            source="backend",
        )
    finally:
        await classifier.stop()


# ---------------------------------------------------------------------------
# Connector Config CRUD (F2 — new)
# ---------------------------------------------------------------------------


@router.get("/connectors", response_model=list[ConnectorConfigResponse])
async def list_connectors() -> list[ConnectorConfigResponse]:
    """List all email connector configurations."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, name, provider, host, port, use_ssl, mailbox,
                          filters, polling_interval_minutes, max_emails_per_fetch,
                          is_active, last_fetched_at, created_at, updated_at
                   FROM email_connector_configs
                   ORDER BY created_at DESC"""
            )
            return [ConnectorConfigResponse(**_row_to_dict(row)) for row in rows]
    except Exception as e:
        logger.error("list_connectors_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/connectors/{config_id}", response_model=ConnectorConfigResponse)
async def get_connector(config_id: str) -> ConnectorConfigResponse:
    """Get a single connector config by ID."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, name, provider, host, port, use_ssl, mailbox,
                          filters, polling_interval_minutes, max_emails_per_fetch,
                          is_active, last_fetched_at, created_at, updated_at
                   FROM email_connector_configs WHERE id::text = $1""",
                config_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail=f"Connector not found: {config_id}")
            return ConnectorConfigResponse(**_row_to_dict(row))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/connectors", response_model=ConnectorConfigResponse, status_code=201)
async def create_connector(config: ConnectorConfigCreate) -> ConnectorConfigResponse:
    """Create a new email connector config."""
    import json as _json

    if config.provider not in ("imap", "o365_graph", "gmail", "outlook_com"):
        raise HTTPException(status_code=400, detail=f"Invalid provider: {config.provider}")

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO email_connector_configs
                       (name, provider, host, port, use_ssl, mailbox,
                        credentials_encrypted, filters,
                        polling_interval_minutes, max_emails_per_fetch)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10)
                   RETURNING id, name, provider, host, port, use_ssl, mailbox,
                             filters, polling_interval_minutes, max_emails_per_fetch,
                             is_active, last_fetched_at, created_at, updated_at""",
                config.name,
                config.provider,
                config.host,
                config.port,
                config.use_ssl,
                config.mailbox,
                config.credentials_encrypted,
                _json.dumps(config.filters),
                config.polling_interval_minutes,
                config.max_emails_per_fetch,
            )
            logger.info("connector_created", name=config.name, provider=config.provider)
            return ConnectorConfigResponse(**_row_to_dict(row))
    except asyncpg.UniqueViolationError as e:
        raise HTTPException(
            status_code=409, detail=f"Connector '{config.name}' already exists"
        ) from e
    except Exception as e:
        logger.error("create_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/connectors/{config_id}", response_model=ConnectorConfigResponse)
async def update_connector(
    config_id: str, update: ConnectorConfigUpdate
) -> ConnectorConfigResponse:
    """Update an existing connector config."""
    import json as _json

    # Build dynamic SET clause
    fields_to_update: dict[str, Any] = {}
    for field_name, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            fields_to_update[field_name] = value

    if not fields_to_update:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Build SET clause dynamically
            set_parts: list[str] = []
            params: list[Any] = [config_id]
            idx = 2
            for k, v in fields_to_update.items():
                if k == "filters":
                    set_parts.append(f"{k} = ${idx}::jsonb")
                    params.append(_json.dumps(v))
                else:
                    set_parts.append(f"{k} = ${idx}")
                    params.append(v)
                idx += 1

            set_parts.append("updated_at = NOW()")
            set_clause = ", ".join(set_parts)

            row = await conn.fetchrow(
                f"""UPDATE email_connector_configs
                    SET {set_clause}
                    WHERE id::text = $1
                    RETURNING id, name, provider, host, port, use_ssl, mailbox,
                              filters, polling_interval_minutes, max_emails_per_fetch,
                              is_active, last_fetched_at, created_at, updated_at""",
                *params,
            )
            if not row:
                raise HTTPException(status_code=404, detail=f"Connector not found: {config_id}")
            logger.info("connector_updated", config_id=config_id)
            return ConnectorConfigResponse(**_row_to_dict(row))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/connectors/{config_id}", status_code=204)
async def delete_connector(config_id: str) -> None:
    """Delete a connector config."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM email_connector_configs WHERE id::text = $1",
                config_id,
            )
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"Connector not found: {config_id}")
            logger.info("connector_deleted", config_id=config_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Test Connection (F2 — new)
# ---------------------------------------------------------------------------


@router.post("/connectors/{config_id}/test", response_model=TestConnectionResponse)
async def test_connector(config_id: str) -> TestConnectionResponse:
    """Test connectivity for a connector config."""
    from sqlalchemy.ext.asyncio import async_sessionmaker as asm

    from aiflow.services.email_connector import EmailConnectorConfig, EmailConnectorService

    engine = await get_engine()
    session_factory = asm(engine, expire_on_commit=False)

    service = EmailConnectorService(session_factory=session_factory, config=EmailConnectorConfig())
    await service.start()

    try:
        result = await service.test_connection(config_id)
        return TestConnectionResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            folders=result.get("folders", []),
            source="backend",
        )
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e), source="backend")
    finally:
        await service.stop()


# ---------------------------------------------------------------------------
# Fetch Emails (F2 — new)
# ---------------------------------------------------------------------------


@router.post("/fetch", response_model=FetchResponse)
async def fetch_emails(request: FetchRequest) -> FetchResponse:
    """Trigger email fetch (non-streaming fallback)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker as asm

    from aiflow.services.email_connector import EmailConnectorConfig, EmailConnectorService

    engine = await get_engine()
    session_factory = asm(engine, expire_on_commit=False)
    since_date = None
    if request.since_days:
        from datetime import timedelta

        since_date = date.today() - timedelta(days=request.since_days)

    service = EmailConnectorService(session_factory=session_factory, config=EmailConnectorConfig())
    await service.start()
    try:
        result = await service.fetch_emails(
            config_id=request.config_id, limit=request.limit, since_date=since_date
        )
        return FetchResponse(
            config_id=request.config_id,
            total_count=result.total_count,
            new_count=result.new_count,
            duration_ms=result.duration_ms,
            error=result.error,
            source="backend",
        )
    except Exception as e:
        return FetchResponse(config_id=request.config_id, error=str(e), source="backend")
    finally:
        await service.stop()


@router.post("/fetch-and-process-stream")
async def fetch_and_process_stream(request: FetchRequest) -> StreamingResponse:
    """Fetch emails + process each through intent pipeline with SSE progress.

    Events: init, file_start, file_step, file_done, file_error, complete.
    Steps per email: fetch, parse, classify, extract, priority, route.
    """
    import time as _t
    import uuid

    from sqlalchemy.ext.asyncio import async_sessionmaker as asm

    from aiflow.services.email_connector import EmailConnectorConfig, EmailConnectorService

    engine = await get_engine()
    session_factory = asm(engine, expire_on_commit=False)
    since_date = None
    if request.since_days:
        from datetime import timedelta

        since_date = date.today() - timedelta(days=request.since_days)

    try:
        from skills.email_intent_processor.workflows.classify import (
            classify_intent as _classify,
        )
        from skills.email_intent_processor.workflows.classify import (
            decide_routing as _route,
        )
        from skills.email_intent_processor.workflows.classify import (
            extract_entities as _extract,
        )
        from skills.email_intent_processor.workflows.classify import (
            parse_email as _parse,
        )
        from skills.email_intent_processor.workflows.classify import (
            score_priority as _priority,
        )

        skill_available = True
    except ImportError:
        skill_available = False

    step_names = ["fetch", "parse", "classify", "extract", "priority", "route"]

    async def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {_json.dumps(obj)}\n\n"

        service = EmailConnectorService(
            session_factory=session_factory, config=EmailConnectorConfig()
        )
        await service.start()

        try:
            # Step 1: Fetch all emails from connector
            result = await service.fetch_emails(
                config_id=request.config_id, limit=request.limit, since_date=since_date
            )

            if result.error:
                yield sse({"event": "error", "error": result.error})
                return

            fetched = result.emails or []
            total = len(fetched)
            yield sse({"event": "init", "total_files": total, "steps": step_names})

            processed = 0
            pool = await get_pool()

            for fi, em in enumerate(fetched):
                fname = em.subject[:60] or em.sender[:40] or f"email_{fi}"
                yield sse(
                    {"event": "file_start", "file": fname, "file_index": fi, "total_files": total}
                )
                await asyncio.sleep(0)

                # Step 0: fetch (already done)
                yield sse(
                    {
                        "event": "file_step",
                        "file": fname,
                        "file_index": fi,
                        "step_index": 0,
                        "step_name": "fetch",
                        "status": "done",
                    }
                )

                eml_path = em.raw_eml_path
                if not eml_path or not Path(eml_path).exists() or not skill_available:
                    yield sse({"event": "file_done", "file": fname, "file_index": fi, "ok": True})
                    continue

                # Steps 1-5: process pipeline
                pipeline = [
                    ("parse", _parse),
                    ("classify", _classify),
                    ("extract", _extract),
                    ("priority", _priority),
                    ("route", _route),
                ]
                data: dict[str, Any] = {
                    "input_file": eml_path,
                    "raw_eml_path": eml_path,
                    "output_dir": str(Path(eml_path).parent),
                }
                file_ok = True

                for si, (sname, sfn) in enumerate(pipeline, 1):
                    yield sse(
                        {
                            "event": "file_step",
                            "file": fname,
                            "file_index": fi,
                            "step_index": si,
                            "step_name": sname,
                            "status": "running",
                        }
                    )
                    await asyncio.sleep(0)
                    t = _t.perf_counter()
                    try:
                        data = await sfn(data)
                        elapsed_ms = int((_t.perf_counter() - t) * 1000)
                        yield sse(
                            {
                                "event": "file_step",
                                "file": fname,
                                "file_index": fi,
                                "step_index": si,
                                "step_name": sname,
                                "status": "done",
                                "elapsed_ms": elapsed_ms,
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            "email_process_step_failed", file=fname, step=sname, error=str(e)
                        )
                        yield sse(
                            {
                                "event": "file_error",
                                "file": fname,
                                "file_index": fi,
                                "step_name": sname,
                                "error": str(e),
                            }
                        )
                        file_ok = False
                        break

                # Store result in workflow_runs
                if file_ok:
                    try:
                        run_id = str(uuid.uuid4())
                        output_data = {
                            "email_id": em.message_id or run_id,
                            "subject": em.subject,
                            "sender": em.sender,
                            "intent": data.get("intent"),
                            "entities": data.get("entities"),
                            "priority": data.get("priority"),
                            "routing": data.get("routing"),
                            "attachment_count": len(em.attachments),
                        }
                        async with pool.acquire() as conn:
                            await conn.execute(
                                """INSERT INTO workflow_runs
                                   (id, workflow_name, workflow_version, skill_name, status,
                                    input_data, output_data, started_at, completed_at, total_duration_ms)
                                   VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,NOW(),NOW(),$8)
                                   ON CONFLICT DO NOTHING""",
                                uuid.UUID(run_id),
                                "email_intent_processing",
                                "1.0",
                                "email_intent_processor",
                                "completed",
                                _json.dumps({"file": eml_path, "subject": em.subject[:100]}),
                                _json.dumps(output_data),
                                0.0,
                            )
                        processed += 1
                    except Exception:
                        pass

                yield sse({"event": "file_done", "file": fname, "file_index": fi, "ok": file_ok})

            yield sse({"event": "complete", "total_fetched": total, "total_processed": processed})

        except Exception as e:
            yield sse({"event": "error", "error": str(e)})
        finally:
            await service.stop()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Scan + Classify (UC3 Sprint K S106 — thin wiring over scan_and_classify)
# ---------------------------------------------------------------------------


@router.post("/scan/{config_id}", response_model=ScanResponse)
async def scan_and_classify_endpoint(config_id: str, req: ScanRequest) -> ScanResponse:
    """Scan an inbox → IntakePackage → classifier → persist to workflow_runs.

    Thin wrapper around ``scan_and_classify``; credentials are read from the
    connector config's plaintext JSON ``credentials_encrypted`` (dev) — real
    credential decryption lands in S107.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker as asm

    from aiflow.policy.intent_routing import IntentRoutingPolicy
    from aiflow.services.classifier.service import ClassifierService
    from aiflow.services.email_connector.orchestrator import scan_and_classify
    from aiflow.sources.email_adapter import EmailSourceAdapter, ImapBackend
    from aiflow.sources.sink import IntakePackageSink
    from aiflow.state.repositories.intake import IntakeRepository
    from aiflow.state.repository import StateRepository

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id::text AS id, provider, host, port, use_ssl, mailbox,
                      credentials_encrypted, is_active
               FROM email_connector_configs
               WHERE id::text = $1""",
            config_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Connector config {config_id} not found")
    if not row["is_active"]:
        raise HTTPException(status_code=400, detail="Connector config is inactive")
    if row["provider"] != "imap":
        raise HTTPException(
            status_code=501,
            detail=f"Provider '{row['provider']}' not yet wired — S107 (IntentRoutingPolicy/providers)",
        )

    try:
        creds = _json.loads(row["credentials_encrypted"] or "{}")
    except _json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=501,
            detail="Encrypted credentials not yet supported — S107 (DPAPI/Fernet decryption)",
        ) from exc

    user = creds.get("user") or creds.get("username")
    password = creds.get("password") or creds.get("pass")
    if not (user and password and row["host"]):
        raise HTTPException(
            status_code=400, detail="Connector config is missing host/user/password"
        )

    backend = ImapBackend(
        host=row["host"],
        port=int(row["port"] or 993),
        user=user,
        password=password,
        mailbox=row["mailbox"] or "INBOX",
        use_ssl=bool(row["use_ssl"]),
    )
    storage_root = Path(os.getenv("AIFLOW_INTAKE_STORAGE", "data/intake_storage")) / config_id
    storage_root.mkdir(parents=True, exist_ok=True)
    adapter = EmailSourceAdapter(
        backend=backend, storage_root=storage_root, tenant_id=req.tenant_id
    )

    intake_repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=intake_repo)

    engine = await get_engine()
    session_factory = asm(engine, expire_on_commit=False)
    state_repo = StateRepository(session_factory)

    routing_policy = None
    if req.routing_policy_id:
        policy_dir = Path(os.getenv("AIFLOW_POLICY_DIR", "config/policies"))
        policy_path = policy_dir / "intent_routing" / f"{req.routing_policy_id}.yaml"
        if not policy_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Routing policy not found: {req.routing_policy_id}",
            )
        try:
            routing_policy = IntentRoutingPolicy.from_yaml(policy_path)
        except (ValueError, OSError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid routing policy YAML: {exc}"
            ) from exc

    classifier = ClassifierService()
    await classifier.start()
    try:
        tuples = await scan_and_classify(
            adapter,
            sink,
            classifier,
            state_repo,
            tenant_id=req.tenant_id,
            max_items=req.max_items,
            schema_labels=req.schema_labels,
            routing_policy=routing_policy,
        )
    except Exception as e:
        logger.exception("scan_and_classify_failed", config_id=config_id, error=str(e))
        return ScanResponse(config_id=config_id, processed=0, error=str(e))
    finally:
        await classifier.stop()

    items = [
        ScanItem(
            package_id=pid,
            label=r.label,
            display_name=r.display_name,
            confidence=r.confidence,
            method=r.method,
        )
        for pid, r in tuples
    ]
    return ScanResponse(config_id=config_id, processed=len(items), items=items)


# ---------------------------------------------------------------------------
# Export (CSV)
# ---------------------------------------------------------------------------


@router.get("/export/csv")
async def export_emails_csv():
    """Export all processed emails as CSV."""
    import csv
    import io

    result = await list_emails(limit=500, offset=0)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "email_id",
            "sender",
            "subject",
            "intent",
            "intent_display_name",
            "confidence",
            "priority",
            "department",
            "queue",
            "received_date",
        ]
    )
    for e in result.emails:
        writer.writerow(
            [
                e.email_id,
                e.sender,
                e.subject,
                e.intent_id or "",
                e.intent_display_name or "",
                e.intent_confidence,
                e.priority_level or "",
                e.department_name or "",
                e.queue_name or "",
                e.received_date or "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aiflow_emails_export.csv"},
    )


# ---------------------------------------------------------------------------
# Fetch History (F2 — new)
# ---------------------------------------------------------------------------


@router.get("/connectors/{config_id}/history", response_model=list[FetchHistoryItem])
async def get_fetch_history(
    config_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> list[FetchHistoryItem]:
    """Get fetch history for a connector."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, config_id, status, email_count, new_emails,
                          duration_ms, error, fetched_at
                   FROM email_fetch_history
                   WHERE config_id::text = $1
                   ORDER BY fetched_at DESC
                   LIMIT $2""",
                config_id,
                limit,
            )
            return [FetchHistoryItem(**_row_to_dict(row)) for row in rows]
    except Exception as e:
        logger.error("fetch_history_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Email Detail (F2.5 — MUST be last to avoid /{email_id} catching /connectors etc)
# ---------------------------------------------------------------------------


@router.get("/{email_id}", response_model=EmailDetailResponse)
async def get_email(email_id: str) -> EmailDetailResponse:
    """Get full email detail by ID (workflow_run id or email_id in output_data)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT r.id, r.output_data, r.input_data, r.started_at, r.total_duration_ms, r.status
                FROM workflow_runs r
                WHERE r.skill_name = 'email_intent_processor'
                  AND (r.id::text = $1 OR r.output_data->>'email_id' = $1)
                LIMIT 1
                """,
                email_id,
            )
            if row:
                data = row["output_data"] or {}
                input_data = row["input_data"] or {}
                return EmailDetailResponse(
                    email_id=data.get("email_id", str(row["id"])),
                    subject=data.get("subject", input_data.get("subject", "")),
                    sender=data.get("sender", input_data.get("sender", "")),
                    recipients=data.get("recipients", []),
                    received_date=row["started_at"].isoformat() if row["started_at"] else None,
                    body=data.get("body", input_data.get("body", ""))[:5000],
                    body_html=data.get("body_html", "")[:5000],
                    intent=data.get("intent"),
                    entities=data.get("entities"),
                    priority=data.get("priority"),
                    routing=data.get("routing"),
                    attachment_summaries=data.get("attachment_summaries", []),
                    processing_time_ms=row["total_duration_ms"] or 0.0,
                    status=row["status"],
                    source="backend",
                )
    except Exception as e:
        logger.warning("email_detail_db_failed", error=str(e), email_id=email_id)

    raise HTTPException(status_code=404, detail=f"Email not found: {email_id}")


# ---------------------------------------------------------------------------
# POST /api/v1/emails/process-batch-stream — process existing .eml files by ID
# ---------------------------------------------------------------------------


class ProcessBatchRequest(BaseModel):
    email_ids: list[str]


@router.post("/process-batch-stream")
async def process_batch_stream(request: ProcessBatchRequest) -> StreamingResponse:
    """Process existing fetched .eml files with per-email SSE progress.

    Scans data/emails/ for matching .eml files and runs the intent pipeline.
    """
    import time as _t
    import uuid

    try:
        from skills.email_intent_processor.workflows.classify import (
            classify_intent as _classify,
        )
        from skills.email_intent_processor.workflows.classify import (
            decide_routing as _route,
        )
        from skills.email_intent_processor.workflows.classify import (
            extract_entities as _extract,
        )
        from skills.email_intent_processor.workflows.classify import (
            parse_email as _parse,
        )
        from skills.email_intent_processor.workflows.classify import (
            score_priority as _priority,
        )
    except ImportError as e:
        err_msg = str(e)

        async def err():
            yield f"data: {_json.dumps({'event': 'error', 'error': err_msg})}\n\n"

        return StreamingResponse(err(), media_type="text/event-stream")

    # Find .eml files matching the email_ids
    email_dir = Path(os.getenv("AIFLOW_EMAIL_DIR", "./data/emails"))
    eml_files: list[tuple[str, Path]] = []
    for eid in request.email_ids:
        # Search recursively for matching .eml
        matches = list(email_dir.rglob(f"{eid}*.eml"))
        if matches:
            eml_files.append((eid, matches[0]))

    step_names = ["parse", "classify", "extract", "priority", "route"]

    async def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {_json.dumps(obj)}\n\n"

        total = len(eml_files)
        yield sse({"event": "init", "total_files": total, "steps": step_names})
        processed = 0
        pool = await get_pool()

        for fi, (eid, eml_path) in enumerate(eml_files):
            # Use subject from .eml as display name
            fname = eml_path.stem[:60]
            yield sse(
                {"event": "file_start", "file": fname, "file_index": fi, "total_files": total}
            )
            await asyncio.sleep(0)

            data: dict[str, Any] = {
                "input_file": str(eml_path),
                "raw_eml_path": str(eml_path),
                "output_dir": str(eml_path.parent),
            }
            pipeline = [
                ("parse", _parse),
                ("classify", _classify),
                ("extract", _extract),
                ("priority", _priority),
                ("route", _route),
            ]
            file_ok = True

            for si, (sname, sfn) in enumerate(pipeline):
                yield sse(
                    {
                        "event": "file_step",
                        "file": fname,
                        "file_index": fi,
                        "step_index": si,
                        "step_name": sname,
                        "status": "running",
                    }
                )
                await asyncio.sleep(0)
                t = _t.perf_counter()
                try:
                    data = await sfn(data)
                    elapsed_ms = int((_t.perf_counter() - t) * 1000)
                    yield sse(
                        {
                            "event": "file_step",
                            "file": fname,
                            "file_index": fi,
                            "step_index": si,
                            "step_name": sname,
                            "status": "done",
                            "elapsed_ms": elapsed_ms,
                        }
                    )
                except Exception as e:
                    yield sse(
                        {
                            "event": "file_error",
                            "file": fname,
                            "file_index": fi,
                            "step_name": sname,
                            "error": str(e),
                        }
                    )
                    file_ok = False
                    break

            # Store to workflow_runs
            if file_ok:
                try:
                    run_id = str(uuid.uuid4())
                    subject = data.get("subject", fname)
                    sender = data.get("sender", "")
                    output_data = {
                        "email_id": eid,
                        "subject": subject,
                        "sender": sender,
                        "intent": data.get("intent"),
                        "entities": data.get("entities"),
                        "priority": data.get("priority"),
                        "routing": data.get("routing"),
                        "attachment_count": len(data.get("attachments", [])),
                    }
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """INSERT INTO workflow_runs
                               (id, workflow_name, workflow_version, skill_name, status,
                                input_data, output_data, started_at, completed_at, total_duration_ms)
                               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,NOW(),NOW(),$8)
                               ON CONFLICT DO NOTHING""",
                            uuid.UUID(run_id),
                            "email_intent_processing",
                            "1.0",
                            "email_intent_processor",
                            "completed",
                            _json.dumps({"file": str(eml_path), "subject": subject[:100]}),
                            _json.dumps(output_data),
                            0.0,
                        )
                    processed += 1
                except Exception:
                    pass

            yield sse({"event": "file_done", "file": fname, "file_index": fi, "ok": file_ok})

        yield sse({"event": "complete", "total_processed": processed})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /api/v1/emails/upload-and-process-stream — SSE per-file progress
# ---------------------------------------------------------------------------


@router.post("/upload-and-process-stream")
async def upload_and_process_stream(
    files: list[UploadFile] = _upload_file_field,
) -> StreamingResponse:
    """Upload + process email files with per-file SSE progress.

    Events: init, file_start, file_step, file_done, file_error, complete.
    Steps per file: upload, parse, classify, extract, priority, route.
    """
    upload_dir = _email_upload_dir()

    try:
        from skills.email_intent_processor.workflows.classify import (
            classify_intent as _classify,
        )
        from skills.email_intent_processor.workflows.classify import (
            decide_routing as _route,
        )
        from skills.email_intent_processor.workflows.classify import (
            extract_entities as _extract,
        )
        from skills.email_intent_processor.workflows.classify import (
            parse_email as _parse,
        )
        from skills.email_intent_processor.workflows.classify import (
            score_priority as _priority,
        )
    except ImportError as e:
        err_msg = str(e)
        logger.error("email_skill_import_failed", error=err_msg)

        async def err():
            yield f"data: {_json.dumps({'event': 'error', 'error': err_msg})}\n\n"

        return StreamingResponse(err(), media_type="text/event-stream")

    per_file_steps = [
        ("upload", None),
        ("parse", _parse),
        ("classify", _classify),
        ("extract", _extract),
        ("priority", _priority),
        ("route", _route),
    ]
    step_names = [s[0] for s in per_file_steps]

    async def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {_json.dumps(obj)}\n\n"

        total = len(files)
        yield sse({"event": "init", "total_files": total, "steps": step_names})

        results = []
        for fi, f in enumerate(files):
            fname = f.filename or f"email_{fi}"
            yield sse(
                {"event": "file_start", "file": fname, "file_index": fi, "total_files": total}
            )
            await asyncio.sleep(0)

            # Step 0: Upload (save to disk)
            yield sse(
                {
                    "event": "file_step",
                    "file": fname,
                    "file_index": fi,
                    "step_index": 0,
                    "step_name": "upload",
                    "status": "running",
                }
            )
            await asyncio.sleep(0)
            ext = Path(fname).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                yield sse(
                    {
                        "event": "file_error",
                        "file": fname,
                        "file_index": fi,
                        "step_name": "upload",
                        "error": f"Invalid extension: {ext}",
                    }
                )
                yield sse({"event": "file_done", "file": fname, "file_index": fi, "ok": False})
                continue
            content = await f.read()
            dest = upload_dir / Path(fname).name
            dest.write_bytes(content)
            yield sse(
                {
                    "event": "file_step",
                    "file": fname,
                    "file_index": fi,
                    "step_index": 0,
                    "step_name": "upload",
                    "status": "done",
                }
            )

            # Steps 1-5: Process pipeline
            output_dir = Path(tempfile.mkdtemp(prefix="aiflow_email_"))
            data: dict[str, Any] = {
                "input_file": str(dest),
                "raw_eml_path": str(dest),
                "output_dir": str(output_dir),
            }
            file_ok = True

            for si in range(1, len(per_file_steps)):
                step_name, step_fn = per_file_steps[si]
                yield sse(
                    {
                        "event": "file_step",
                        "file": fname,
                        "file_index": fi,
                        "step_index": si,
                        "step_name": step_name,
                        "status": "running",
                    }
                )
                await asyncio.sleep(0)
                t = _time.perf_counter()
                try:
                    data = await step_fn(data)  # type: ignore[misc]
                    elapsed_ms = int((_time.perf_counter() - t) * 1000)
                    yield sse(
                        {
                            "event": "file_step",
                            "file": fname,
                            "file_index": fi,
                            "step_index": si,
                            "step_name": step_name,
                            "status": "done",
                            "elapsed_ms": elapsed_ms,
                        }
                    )
                except Exception as e:
                    logger.error(
                        "email_stream_step_failed", file=fname, step=step_name, error=str(e)
                    )
                    yield sse(
                        {
                            "event": "file_error",
                            "file": fname,
                            "file_index": fi,
                            "step_name": step_name,
                            "error": str(e),
                        }
                    )
                    file_ok = False
                    break

            if file_ok:
                results.append(
                    {
                        "file": fname,
                        "intent": data.get("intent", {}).get("intent_id")
                        if isinstance(data.get("intent"), dict)
                        else data.get("intent"),
                        "priority": data.get("priority", {}).get("priority_name")
                        if isinstance(data.get("priority"), dict)
                        else None,
                    }
                )
            yield sse({"event": "file_done", "file": fname, "file_index": fi, "ok": file_ok})

        yield sse({"event": "complete", "results": results, "total_processed": len(results)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
