"""Email processing API — list, detail, upload, process, classify, connector config CRUD, fetch."""
from __future__ import annotations

import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/emails", tags=["emails"])

ALLOWED_EXTENSIONS = {".eml", ".msg", ".txt"}


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_url() -> str:
    return os.getenv(
        "AIFLOW_DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )


def _email_upload_dir() -> Path:
    d = Path(os.getenv("AIFLOW_EMAIL_UPLOAD_DIR", "./data/uploads/emails"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    """Convert asyncpg Record to dict, serializing datetimes and UUIDs."""
    import uuid as _uuid
    import json as _json
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
                        return EmailListResponse(emails=emails, total=len(emails), source="demo")
                except Exception:
                    pass
                break

    return EmailListResponse(emails=emails, total=total, source="backend")


# ---------------------------------------------------------------------------
# Upload & Process (existing)
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=EmailUploadResponse)
async def upload_emails(files: list[UploadFile] = File(...)) -> EmailUploadResponse:
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
        from skills.email_intent_processor.workflows.pipeline import (
            parse_email as _parse,
            classify_intent as _classify,
            extract_entities as _extract,
            determine_priority as _priority,
            route_email as _route,
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
    from aiflow.services.classifier import ClassifierService, ClassifierConfig

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
        conn = await asyncpg.connect(_get_db_url())
        try:
            rows = await conn.fetch(
                """SELECT id, name, provider, host, port, use_ssl, mailbox,
                          filters, polling_interval_minutes, max_emails_per_fetch,
                          is_active, last_fetched_at, created_at, updated_at
                   FROM email_connector_configs
                   ORDER BY created_at DESC"""
            )
            return [
                ConnectorConfigResponse(**_row_to_dict(row))
                for row in rows
            ]
        finally:
            await conn.close()
    except Exception as e:
        logger.error("list_connectors_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{config_id}", response_model=ConnectorConfigResponse)
async def get_connector(config_id: str) -> ConnectorConfigResponse:
    """Get a single connector config by ID."""
    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
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
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors", response_model=ConnectorConfigResponse, status_code=201)
async def create_connector(config: ConnectorConfigCreate) -> ConnectorConfigResponse:
    """Create a new email connector config."""
    import json as _json

    if config.provider not in ("imap", "o365_graph", "gmail"):
        raise HTTPException(status_code=400, detail=f"Invalid provider: {config.provider}")

    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
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
        finally:
            await conn.close()
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"Connector '{config.name}' already exists")
    except Exception as e:
        logger.error("create_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/connectors/{config_id}", response_model=ConnectorConfigResponse)
async def update_connector(config_id: str, update: ConnectorConfigUpdate) -> ConnectorConfigResponse:
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
        conn = await asyncpg.connect(_get_db_url())
        try:
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

            set_parts.append(f"updated_at = NOW()")
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
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connectors/{config_id}", status_code=204)
async def delete_connector(config_id: str) -> None:
    """Delete a connector config."""
    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
            result = await conn.execute(
                "DELETE FROM email_connector_configs WHERE id::text = $1",
                config_id,
            )
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"Connector not found: {config_id}")
            logger.info("connector_deleted", config_id=config_id)
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_connector_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Test Connection (F2 — new)
# ---------------------------------------------------------------------------

@router.post("/connectors/{config_id}/test", response_model=TestConnectionResponse)
async def test_connector(config_id: str) -> TestConnectionResponse:
    """Test connectivity for a connector config."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker as asm
    from aiflow.services.email_connector import EmailConnectorService, EmailConnectorConfig

    db_url = _get_db_url().replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
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
        await engine.dispose()


# ---------------------------------------------------------------------------
# Fetch Emails (F2 — new)
# ---------------------------------------------------------------------------

@router.post("/fetch", response_model=FetchResponse)
async def fetch_emails(request: FetchRequest) -> FetchResponse:
    """Trigger email fetch from a configured connector."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker as asm
    from aiflow.services.email_connector import EmailConnectorService, EmailConnectorConfig

    db_url = _get_db_url().replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    session_factory = asm(engine, expire_on_commit=False)

    since_date = None
    if request.since_days:
        from datetime import timedelta
        since_date = date.today() - timedelta(days=request.since_days)

    service = EmailConnectorService(session_factory=session_factory, config=EmailConnectorConfig())
    await service.start()

    try:
        result = await service.fetch_emails(
            config_id=request.config_id,
            limit=request.limit,
            since_date=since_date,
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
        logger.error("fetch_failed", error=str(e))
        return FetchResponse(
            config_id=request.config_id,
            error=str(e),
            source="backend",
        )
    finally:
        await service.stop()
        await engine.dispose()


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
        conn = await asyncpg.connect(_get_db_url())
        try:
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
        finally:
            await conn.close()
    except Exception as e:
        logger.error("fetch_history_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Email Detail (F2.5 — MUST be last to avoid /{email_id} catching /connectors etc)
# ---------------------------------------------------------------------------

@router.get("/{email_id}", response_model=EmailDetailResponse)
async def get_email(email_id: str) -> EmailDetailResponse:
    """Get full email detail by ID (workflow_run id or email_id in output_data)."""
    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
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
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("email_detail_db_failed", error=str(e), email_id=email_id)

    # Fallback: check JSON files
    import json as _json
    for base in [Path("aiflow-ui/data"), Path("aiflow-ui/public/data")]:
        f = base / "emails.json"
        if f.exists():
            try:
                raw = _json.loads(f.read_text(encoding="utf-8"))
                items = raw if isinstance(raw, list) else raw.get("emails", [])
                for item in items:
                    if item.get("email_id") == email_id:
                        return EmailDetailResponse(
                            email_id=item["email_id"],
                            subject=item.get("subject", ""),
                            sender=item.get("sender", ""),
                            body=item.get("body", "")[:5000],
                            intent=item.get("intent"),
                            entities=item.get("entities"),
                            priority=item.get("priority"),
                            routing=item.get("routing"),
                            attachment_summaries=item.get("attachment_summaries", []),
                            source="demo",
                        )
            except Exception:
                pass
            break

    raise HTTPException(status_code=404, detail=f"Email not found: {email_id}")
