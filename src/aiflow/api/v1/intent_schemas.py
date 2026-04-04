"""Intent schema CRUD API — manage intent definitions for email/document classification.

Schemas stored in DB (intent_schemas table) and loadable from YAML/JSON files.
Each schema defines intents with keywords, examples, routing rules, and ML labels.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/intent-schemas", tags=["intent-schemas"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class IntentRouting(BaseModel):
    queue: str = ""
    priority_boost: int = 0
    sla_hours: int = 48


class IntentDefinition(BaseModel):
    id: str
    display_name: str = ""
    description: str = ""
    keywords_hu: list[str] = Field(default_factory=list)
    keywords_en: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    routing: IntentRouting = Field(default_factory=IntentRouting)
    ml_label: str = ""
    sub_intents: list[str] = Field(default_factory=list)
    auto_action: str | None = None


class IntentSchemaItem(BaseModel):
    """A complete intent schema with metadata."""

    id: str
    name: str
    version: str = "1.0"
    description: str = ""
    intents: list[IntentDefinition] = Field(default_factory=list)
    customer: str = "default"
    created_at: str | None = None
    updated_at: str | None = None


class IntentSchemaListResponse(BaseModel):
    schemas: list[IntentSchemaItem]
    total: int
    source: str = "backend"


class IntentSchemaCreateRequest(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    intents: list[IntentDefinition] = Field(default_factory=list)
    customer: str = "default"


class IntentSchemaUpdateRequest(BaseModel):
    name: str | None = None
    version: str | None = None
    description: str | None = None
    intents: list[IntentDefinition] | None = None
    customer: str | None = None


class IntentSchemaResponse(BaseModel):
    schema_item: IntentSchemaItem = Field(alias="schema")
    source: str = "backend"

    model_config = {"populate_by_name": True}


class IntentTestRequest(BaseModel):
    text: str
    language: str = "hu"


class IntentTestResult(BaseModel):
    intent_id: str
    intent_name: str
    confidence: float
    matched_keywords: list[str] = Field(default_factory=list)


class IntentTestResponse(BaseModel):
    text: str
    results: list[IntentTestResult]
    model_used: str = "keyword-matching"
    source: str = "backend"


# ---------------------------------------------------------------------------
# Table setup helper
# ---------------------------------------------------------------------------


async def _ensure_table(pool: Any) -> None:
    """Create intent_schemas table if it doesn't exist (idempotent)."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS intent_schemas (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT '1.0',
                description TEXT DEFAULT '',
                intents JSONB DEFAULT '[]'::jsonb,
                customer TEXT DEFAULT 'default',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(name, customer)
            )
        """)


# ---------------------------------------------------------------------------
# GET /api/v1/intent-schemas — list all schemas
# ---------------------------------------------------------------------------


@router.get("", response_model=IntentSchemaListResponse)
async def list_intent_schemas(
    customer: str = Query("default"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> IntentSchemaListResponse:
    """List all intent schemas, optionally filtered by customer."""
    try:
        pool = await get_pool()
        await _ensure_table(pool)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, version, description, intents, customer,
                       created_at, updated_at
                FROM intent_schemas
                WHERE customer = $1 OR customer = 'default'
                ORDER BY name
                LIMIT $2 OFFSET $3
                """,
                customer,
                limit,
                offset,
            )
            count_row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM intent_schemas"
                " WHERE customer = $1 OR customer = 'default'",
                customer,
            )
            total = count_row["cnt"] if count_row else 0

        schemas = [_row_to_schema(row) for row in rows]
        return IntentSchemaListResponse(schemas=schemas, total=total)

    except Exception as e:
        logger.error("list_intent_schemas_failed", error=str(e))
        return IntentSchemaListResponse(schemas=[], total=0)


# ---------------------------------------------------------------------------
# GET /api/v1/intent-schemas/{schema_id} — get single schema
# ---------------------------------------------------------------------------


@router.get("/{schema_id}", response_model=IntentSchemaResponse)
async def get_intent_schema(schema_id: str) -> IntentSchemaResponse:
    """Get a single intent schema by ID."""
    pool = await get_pool()
    await _ensure_table(pool)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, name, version, description, intents, customer,
                   created_at, updated_at
            FROM intent_schemas WHERE id = $1::uuid
            """,
            uuid.UUID(schema_id),
        )

    if not row:
        raise HTTPException(status_code=404, detail=f"Intent schema not found: {schema_id}")

    return IntentSchemaResponse(schema=_row_to_schema(row))


# ---------------------------------------------------------------------------
# POST /api/v1/intent-schemas — create new schema
# ---------------------------------------------------------------------------


@router.post("", response_model=IntentSchemaResponse, status_code=201)
async def create_intent_schema(request: IntentSchemaCreateRequest) -> IntentSchemaResponse:
    """Create a new intent schema."""
    pool = await get_pool()
    await _ensure_table(pool)

    schema_id = uuid.uuid4()
    intents_json = json.dumps([i.model_dump() for i in request.intents])

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO intent_schemas (id, name, version, description, intents, customer)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                schema_id,
                request.name,
                request.version,
                request.description,
                intents_json,
                request.customer,
            )

            row = await conn.fetchrow(
                """
                SELECT id, name, version, description, intents, customer,
                       created_at, updated_at
                FROM intent_schemas WHERE id = $1
                """,
                schema_id,
            )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Intent schema '{request.name}' already exists"
                    f" for customer '{request.customer}'"
                ),
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e

    logger.info("intent_schema_created", id=str(schema_id), name=request.name)
    return IntentSchemaResponse(schema=_row_to_schema(row))


# ---------------------------------------------------------------------------
# PUT /api/v1/intent-schemas/{schema_id} — update schema
# ---------------------------------------------------------------------------


@router.put("/{schema_id}", response_model=IntentSchemaResponse)
async def update_intent_schema(
    schema_id: str, request: IntentSchemaUpdateRequest
) -> IntentSchemaResponse:
    """Update an existing intent schema."""
    pool = await get_pool()
    await _ensure_table(pool)

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM intent_schemas WHERE id = $1::uuid",
            uuid.UUID(schema_id),
        )
        if not existing:
            raise HTTPException(status_code=404, detail=f"Intent schema not found: {schema_id}")

        # Build dynamic update
        updates: list[str] = ["updated_at = NOW()"]
        params: list[Any] = []
        idx = 1

        if request.name is not None:
            updates.append(f"name = ${idx}")
            params.append(request.name)
            idx += 1
        if request.version is not None:
            updates.append(f"version = ${idx}")
            params.append(request.version)
            idx += 1
        if request.description is not None:
            updates.append(f"description = ${idx}")
            params.append(request.description)
            idx += 1
        if request.intents is not None:
            updates.append(f"intents = ${idx}::jsonb")
            params.append(json.dumps([i.model_dump() for i in request.intents]))
            idx += 1
        if request.customer is not None:
            updates.append(f"customer = ${idx}")
            params.append(request.customer)
            idx += 1

        params.append(uuid.UUID(schema_id))
        query = f"UPDATE intent_schemas SET {', '.join(updates)} WHERE id = ${idx}::uuid"
        await conn.execute(query, *params)

        row = await conn.fetchrow(
            """
            SELECT id, name, version, description, intents, customer,
                   created_at, updated_at
            FROM intent_schemas WHERE id = $1::uuid
            """,
            uuid.UUID(schema_id),
        )

    logger.info("intent_schema_updated", id=schema_id)
    return IntentSchemaResponse(schema=_row_to_schema(row))


# ---------------------------------------------------------------------------
# DELETE /api/v1/intent-schemas/{schema_id} — delete schema
# ---------------------------------------------------------------------------


@router.delete("/{schema_id}", status_code=204)
async def delete_intent_schema(schema_id: str) -> None:
    """Delete an intent schema."""
    pool = await get_pool()
    await _ensure_table(pool)

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM intent_schemas WHERE id = $1::uuid",
            uuid.UUID(schema_id),
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail=f"Intent schema not found: {schema_id}")

    logger.info("intent_schema_deleted", id=schema_id)


# ---------------------------------------------------------------------------
# POST /api/v1/intent-schemas/{schema_id}/test — test classification
# ---------------------------------------------------------------------------


@router.post("/{schema_id}/test", response_model=IntentTestResponse)
async def test_intent_schema(schema_id: str, request: IntentTestRequest) -> IntentTestResponse:
    """Test a text against a schema's intents using keyword matching.

    Returns ranked intent matches with confidence scores.
    For production classification, use the email_intent_processor skill.
    """
    pool = await get_pool()
    await _ensure_table(pool)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT intents FROM intent_schemas WHERE id = $1::uuid",
            uuid.UUID(schema_id),
        )

    if not row:
        raise HTTPException(status_code=404, detail=f"Intent schema not found: {schema_id}")

    intents_raw = row["intents"]
    intents_data = intents_raw if isinstance(intents_raw, list) else json.loads(intents_raw)
    text_lower = request.text.lower()

    # Keyword-based scoring
    results: list[IntentTestResult] = []
    for intent in intents_data:
        keywords = intent.get(f"keywords_{request.language}", intent.get("keywords_hu", []))
        matched = [kw for kw in keywords if kw.lower() in text_lower]

        # Also check examples for similarity (simple substring match)
        example_matches = sum(
            1
            for ex in intent.get("examples", [])
            if any(word in text_lower for word in ex.lower().split() if len(word) > 3)
        )

        total_score = len(matched) * 2 + example_matches
        if total_score > 0:
            confidence = min(1.0, total_score / 10.0)
            results.append(
                IntentTestResult(
                    intent_id=intent.get("id", ""),
                    intent_name=intent.get("display_name", intent.get("id", "")),
                    confidence=round(confidence, 2),
                    matched_keywords=matched,
                )
            )

    # Sort by confidence descending
    results.sort(key=lambda r: r.confidence, reverse=True)

    return IntentTestResponse(
        text=request.text,
        results=results[:5],
        model_used="keyword-matching",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_schema(row: Any) -> IntentSchemaItem:
    """Convert a DB row to IntentSchemaItem."""
    intents_raw = row["intents"]
    if isinstance(intents_raw, str):
        intents_raw = json.loads(intents_raw)

    intents = []
    for i in intents_raw or []:
        routing_data = i.get("routing", {})
        intents.append(
            IntentDefinition(
                id=i.get("id", ""),
                display_name=i.get("display_name", ""),
                description=i.get("description", ""),
                keywords_hu=i.get("keywords_hu", []),
                keywords_en=i.get("keywords_en", []),
                examples=i.get("examples", []),
                routing=IntentRouting(**routing_data) if routing_data else IntentRouting(),
                ml_label=i.get("ml_label", ""),
                sub_intents=i.get("sub_intents", []),
                auto_action=i.get("auto_action"),
            )
        )

    return IntentSchemaItem(
        id=str(row["id"]),
        name=row["name"],
        version=row["version"] or "1.0",
        description=row["description"] or "",
        intents=intents,
        customer=row["customer"] or "default",
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
    )
