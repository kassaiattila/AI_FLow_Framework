"""RoutingRunRepository — Sprint X / SX-3 audit-log writer + reader.

Persists every UC3 EXTRACT email's dispatch trail to the
``routing_runs`` table (Alembic 050) and exposes async list / get /
aggregate helpers that the ``/api/v1/routing-runs`` router consumes.

The metadata JSONB cap (8 KB) is enforced here at write-time. When a
serialised payload would exceed the cap, per-attachment entries are
dropped one-at-a-time from the END of the array (newest-last; oldest-
first kept) and the ``metadata_truncated`` / ``metadata_truncated_count``
fields are populated so operators see the truncation in the UI detail
drawer. A WARN-level structlog event records the truncation count.

Reuses the asyncpg pool created in :mod:`aiflow.api.deps`. SQL is raw +
parameterised (matches the sibling
:class:`aiflow.services.document_recognizer.repository.DocRecognitionRepository`
style — no SQLAlchemy ORM in this layer).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import structlog

from aiflow.services.routing_runs.schemas import (
    RoutingRunCreate,
    RoutingRunDetail,
    RoutingRunFilters,
    RoutingRunSummary,
    RoutingStatsBucket,
    RoutingStatsResponse,
)

__all__ = [
    "METADATA_BYTE_CAP",
    "RoutingRunRepository",
]

logger = structlog.get_logger(__name__)


METADATA_BYTE_CAP = 8 * 1024
"""8 KB cap on the JSONB ``metadata`` payload at write time.

Sprint X / SX-3 design point: per-attachment detail (filename hash +
doctype + outcome + per-field cost/latency) fits comfortably under 8 KB
for realistic emails. A consistently-truncating workload triggers the
SOFT STOP in NEXT.md (bump cap to 16 KB or split into a
``routing_run_attachments`` sidecar table — deferred to extension
session).
"""


class RoutingRunRepository:
    """Async repository for ``routing_runs`` (Alembic 050)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Write side
    # ------------------------------------------------------------------

    async def insert(self, row: RoutingRunCreate) -> uuid.UUID:
        """Insert one audit row. Returns the generated UUID.

        Enforces the 8 KB ``metadata`` cap by trimming per-attachment
        entries from the tail of the ``metadata['attachments']`` array
        until the serialised payload fits. Truncation count + boolean
        are stored alongside the JSONB so the UI drawer can flag the
        truncation to the operator.
        """
        run_id = uuid.uuid4()
        metadata_payload, truncated_count = _cap_metadata(row.metadata)
        metadata_json = json.dumps(metadata_payload) if metadata_payload is not None else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO routing_runs (
                    id, tenant_id, email_id, intent_class,
                    doctype_detected, doctype_confidence,
                    extraction_path, extraction_outcome,
                    cost_usd, latency_ms, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb
                )
                """,
                run_id,
                row.tenant_id,
                row.email_id,
                row.intent_class,
                row.doctype_detected,
                row.doctype_confidence,
                row.extraction_path,
                row.extraction_outcome,
                row.cost_usd,
                row.latency_ms,
                metadata_json,
            )

        logger.info(
            "routing_run.inserted",
            run_id=str(run_id),
            tenant_id=row.tenant_id,
            email_id=str(row.email_id) if row.email_id else None,
            extraction_path=row.extraction_path,
            extraction_outcome=row.extraction_outcome,
            doctype_detected=row.doctype_detected,
            metadata_truncated_count=truncated_count,
        )
        if truncated_count > 0:
            logger.warning(
                "routing_run.metadata_truncated",
                run_id=str(run_id),
                tenant_id=row.tenant_id,
                truncated_count=truncated_count,
                cap_bytes=METADATA_BYTE_CAP,
            )

        return run_id

    # ------------------------------------------------------------------
    # Read side
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        filters: RoutingRunFilters,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RoutingRunSummary]:
        """List rows matching ``filters`` ordered by ``created_at DESC``."""
        sql, params = _build_list_sql(filters, limit=limit, offset=offset, columns="summary")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [_row_to_summary(r) for r in rows]

    async def get(self, run_id: uuid.UUID, *, tenant_id: str) -> RoutingRunDetail | None:
        """Fetch one row scoped to ``tenant_id``. Returns ``None`` on miss
        OR cross-tenant ID collision (no leakage)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    id, tenant_id, email_id, intent_class,
                    doctype_detected, doctype_confidence,
                    extraction_path, extraction_outcome,
                    cost_usd, latency_ms, metadata, created_at
                FROM routing_runs
                WHERE id = $1 AND tenant_id = $2
                """,
                run_id,
                tenant_id,
            )
        if row is None:
            return None
        return _row_to_detail(row)

    async def aggregate_stats(
        self,
        *,
        tenant_id: str,
        since: datetime,
        until: datetime,
    ) -> RoutingStatsResponse:
        """Compute distribution + cost/latency stats for ``[since, until)``.

        Empty windows return ``total_runs=0`` with empty distribution
        lists and zeroed centiles (no division-by-zero, no errors).
        """
        async with self._pool.acquire() as conn:
            stats_row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_runs,
                    COALESCE(AVG(cost_usd), 0) AS mean_cost,
                    COALESCE(
                        PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY latency_ms
                        ) FILTER (WHERE latency_ms IS NOT NULL),
                        0
                    ) AS p50_latency,
                    COALESCE(
                        PERCENTILE_CONT(0.95) WITHIN GROUP (
                            ORDER BY latency_ms
                        ) FILTER (WHERE latency_ms IS NOT NULL),
                        0
                    ) AS p95_latency
                FROM routing_runs
                WHERE tenant_id = $1
                  AND created_at >= $2
                  AND created_at < $3
                """,
                tenant_id,
                since,
                until,
            )
            doctype_rows = await conn.fetch(
                """
                SELECT COALESCE(doctype_detected, '<none>') AS key, COUNT(*) AS count
                FROM routing_runs
                WHERE tenant_id = $1 AND created_at >= $2 AND created_at < $3
                GROUP BY COALESCE(doctype_detected, '<none>')
                ORDER BY count DESC
                """,
                tenant_id,
                since,
                until,
            )
            outcome_rows = await conn.fetch(
                """
                SELECT extraction_outcome AS key, COUNT(*) AS count
                FROM routing_runs
                WHERE tenant_id = $1 AND created_at >= $2 AND created_at < $3
                GROUP BY extraction_outcome
                ORDER BY count DESC
                """,
                tenant_id,
                since,
                until,
            )
            path_rows = await conn.fetch(
                """
                SELECT extraction_path AS key, COUNT(*) AS count
                FROM routing_runs
                WHERE tenant_id = $1 AND created_at >= $2 AND created_at < $3
                GROUP BY extraction_path
                ORDER BY count DESC
                """,
                tenant_id,
                since,
                until,
            )

        return RoutingStatsResponse(
            since=since,
            until=until,
            total_runs=int(stats_row["total_runs"] or 0),
            by_doctype=[
                RoutingStatsBucket(key=str(r["key"]), count=int(r["count"])) for r in doctype_rows
            ],
            by_outcome=[
                RoutingStatsBucket(key=str(r["key"]), count=int(r["count"])) for r in outcome_rows
            ],
            by_extraction_path=[
                RoutingStatsBucket(key=str(r["key"]), count=int(r["count"])) for r in path_rows
            ],
            mean_cost_usd=float(stats_row["mean_cost"] or 0.0),
            p50_latency_ms=float(stats_row["p50_latency"] or 0.0),
            p95_latency_ms=float(stats_row["p95_latency"] or 0.0),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def default_stats_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Default 7-day window used when the router omits ``since`` / ``until``."""
    until = now or datetime.now(UTC)
    since = until - timedelta(days=7)
    return since, until


def _build_list_sql(
    filters: RoutingRunFilters,
    *,
    limit: int,
    offset: int,
    columns: str,
) -> tuple[str, list[Any]]:
    """Compose a parameterised list SQL string + parameter sequence."""
    select_cols = (
        "id, tenant_id, email_id, intent_class, doctype_detected, "
        "doctype_confidence, extraction_path, extraction_outcome, "
        "cost_usd, latency_ms, created_at"
    )
    if columns == "detail":
        select_cols += ", metadata"

    where: list[str] = []
    params: list[Any] = []

    def _bind(value: Any) -> str:
        params.append(value)
        return f"${len(params)}"

    if filters.tenant_id is not None:
        where.append(f"tenant_id = {_bind(filters.tenant_id)}")
    if filters.intent_class is not None:
        where.append(f"intent_class = {_bind(filters.intent_class)}")
    if filters.doctype_detected is not None:
        where.append(f"doctype_detected = {_bind(filters.doctype_detected)}")
    if filters.extraction_outcome is not None:
        where.append(f"extraction_outcome = {_bind(filters.extraction_outcome)}")
    if filters.since is not None:
        where.append(f"created_at >= {_bind(filters.since)}")
    if filters.until is not None:
        where.append(f"created_at < {_bind(filters.until)}")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    limit_param = _bind(limit)
    offset_param = _bind(offset)

    sql = (
        f"SELECT {select_cols} FROM routing_runs "
        f"{where_clause} "
        f"ORDER BY created_at DESC "
        f"LIMIT {limit_param} OFFSET {offset_param}"
    )
    return sql, params


def _row_to_summary(row: asyncpg.Record) -> RoutingRunSummary:
    return RoutingRunSummary(
        id=row["id"],
        tenant_id=row["tenant_id"],
        email_id=row["email_id"],
        intent_class=row["intent_class"],
        doctype_detected=row["doctype_detected"],
        doctype_confidence=row["doctype_confidence"],
        extraction_path=row["extraction_path"],
        extraction_outcome=row["extraction_outcome"],
        cost_usd=row["cost_usd"],
        latency_ms=row["latency_ms"],
        created_at=row["created_at"],
    )


def _row_to_detail(row: asyncpg.Record) -> RoutingRunDetail:
    raw_metadata = row["metadata"]
    metadata: dict[str, Any] | None
    truncated = False
    truncated_count = 0
    if raw_metadata is None:
        metadata = None
    else:
        if isinstance(raw_metadata, str):
            try:
                metadata = json.loads(raw_metadata)
            except (TypeError, ValueError):
                metadata = None
        elif isinstance(raw_metadata, dict):
            metadata = raw_metadata
        else:
            metadata = None
        if isinstance(metadata, dict):
            truncated_flag = metadata.get("_truncated")
            if isinstance(truncated_flag, bool):
                truncated = truncated_flag
            try:
                truncated_count = int(metadata.get("_truncated_count") or 0)
            except (TypeError, ValueError):
                truncated_count = 0

    return RoutingRunDetail(
        id=row["id"],
        tenant_id=row["tenant_id"],
        email_id=row["email_id"],
        intent_class=row["intent_class"],
        doctype_detected=row["doctype_detected"],
        doctype_confidence=row["doctype_confidence"],
        extraction_path=row["extraction_path"],
        extraction_outcome=row["extraction_outcome"],
        cost_usd=row["cost_usd"],
        latency_ms=row["latency_ms"],
        created_at=row["created_at"],
        metadata=metadata,
        metadata_truncated=truncated,
        metadata_truncated_count=truncated_count,
    )


def _cap_metadata(
    metadata: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, int]:
    """Trim the ``metadata['attachments']`` array until the serialised
    payload fits inside :data:`METADATA_BYTE_CAP`.

    Strategy:
        1. Serialise the candidate payload.
        2. If it fits → return as-is, no truncation.
        3. Otherwise drop the LAST attachment entry (newest-last;
           per-attachment order is preserved by SX-2 so dropping the
           tail keeps the oldest / earliest-classified entries).
        4. Repeat until either the payload fits OR the attachment list
           is empty (in which case persist whatever is left, with the
           ``_truncated_overflow`` flag set so operators can spot the
           extreme case in the UI drawer).

    Returns the (possibly-trimmed) metadata dict + the count of
    attachments that were dropped.
    """
    if metadata is None:
        return None, 0
    if not isinstance(metadata, dict):
        # Non-dict metadata: best-effort serialisation, no truncation
        # because there is no list-of-attachments invariant to honour.
        try:
            blob = json.dumps(metadata)
        except (TypeError, ValueError):
            return None, 0
        if len(blob.encode("utf-8")) <= METADATA_BYTE_CAP:
            return metadata, 0
        # Fall back to an empty dict + explicit overflow flag so the
        # row still lands.
        return {"_truncated_overflow": True}, 0

    payload = dict(metadata)
    blob = json.dumps(payload)
    if len(blob.encode("utf-8")) <= METADATA_BYTE_CAP:
        return payload, 0

    attachments = payload.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        # No attachment array we can shrink — drop the heaviest top-
        # level keys until it fits, or fall back to the marker dict.
        return _cap_metadata_no_attachments(payload)

    truncated_count = 0
    payload["attachments"] = list(attachments)
    while payload["attachments"]:
        payload["_truncated"] = True
        payload["_truncated_count"] = truncated_count + 1
        payload["attachments"].pop()
        truncated_count += 1
        blob = json.dumps(payload)
        if len(blob.encode("utf-8")) <= METADATA_BYTE_CAP:
            payload["_truncated_count"] = truncated_count
            return payload, truncated_count

    # Pathological: even with zero attachments the surrounding payload
    # is too big. Drop everything but the marker.
    return (
        {
            "_truncated": True,
            "_truncated_count": truncated_count,
            "_truncated_overflow": True,
        },
        truncated_count,
    )


def _cap_metadata_no_attachments(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Fallback for metadata dicts that don't carry an attachments list.

    Drops top-level keys in descending size order until the payload
    fits or only the marker remains. Returns ``truncated_count=0``
    because the unit is not "attachments dropped" here — top-level key
    drops are recorded under ``_truncated_keys_dropped``.
    """
    candidates = sorted(
        ((k, len(json.dumps(v))) for k, v in payload.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    dropped: list[str] = []
    for key, _size in candidates:
        if key.startswith("_"):
            continue
        payload.pop(key, None)
        dropped.append(key)
        payload["_truncated"] = True
        payload["_truncated_keys_dropped"] = dropped
        blob = json.dumps(payload)
        if len(blob.encode("utf-8")) <= METADATA_BYTE_CAP:
            return payload, 0
    return (
        {
            "_truncated": True,
            "_truncated_keys_dropped": dropped,
            "_truncated_overflow": True,
        },
        0,
    )
