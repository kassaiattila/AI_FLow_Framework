"""DocRecognitionRepository — Sprint V SV-3 audit-log writer.

Persists ``recognize_and_extract`` outcomes to the ``doc_recognition_runs``
table (Alembic 048). The PII redaction boundary lives here: when the
descriptor's ``intent_routing.pii_redaction`` is True, field VALUES are
replaced with the literal string ``"<redacted>"`` BEFORE the row is
written. Field NAMES + confidences + extraction metadata stay intact for
forensic / observability use.

Operators with the ``aiflow.security:pii_unredact`` permission may at a
future date hold a separate column-level encrypted blob; out of scope
for SV-3 (deferred to post-Sprint-V audit per the Sprint V plan §6).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg
import structlog

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocIntentDecision,
    DocTypeMatch,
)

__all__ = ["DocRecognitionRepository"]

logger = structlog.get_logger(__name__)


class DocRecognitionRepository:
    """Async repository for ``doc_recognition_runs`` (Alembic 048)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert_run(
        self,
        *,
        tenant_id: str,
        match: DocTypeMatch,
        extraction: DocExtractionResult,
        intent: DocIntentDecision,
        filename_hint: str | None = None,
        classification_method: str = "rule_engine",
        pii_redaction: bool = False,
    ) -> uuid.UUID:
        """Insert one audit row. Returns the generated UUID.

        Args:
            tenant_id: tenant attribution (matches the request envelope).
            match: classifier output.
            extraction: per-field extraction result. PII redaction (if
                enabled) replaces every value with ``"<redacted>"``;
                confidences + field names are preserved.
            intent: routing decision after extraction.
            filename_hint: original filename (for forensic correlation;
                operators are expected to scrub PII from the filename
                upstream where applicable).
            classification_method: ``rule_engine`` / ``llm_fallback`` /
                ``hint`` — drives the per-source histogram in the
                operator dashboard.
            pii_redaction: when True, ``extracted_fields_jsonb`` values
                are replaced with ``"<redacted>"``. Driven by the
                descriptor's ``intent_routing.pii_redaction`` flag.
        """
        run_id = uuid.uuid4()

        # Build the redacted (or pass-through) extracted_fields payload.
        fields_payload: dict[str, dict[str, Any]] = {}
        for name, fv in extraction.extracted_fields.items():
            value: Any = "<redacted>" if pii_redaction else fv.value
            fields_payload[name] = {
                "value": value,
                "confidence": fv.confidence,
            }

        alternatives_payload = [
            {"doc_type": alt_name, "confidence": alt_conf}
            for alt_name, alt_conf in match.alternatives
        ]

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO doc_recognition_runs (
                    id, tenant_id, doc_type, confidence, alternatives_jsonb,
                    extracted_fields_jsonb, intent, intent_reason, cost_usd,
                    extraction_time_ms, filename_hint, classification_method,
                    pii_redacted
                ) VALUES (
                    $1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9, $10, $11, $12, $13
                )
                """,
                run_id,
                tenant_id,
                match.doc_type,
                float(match.confidence),
                json.dumps(alternatives_payload),
                json.dumps(fields_payload),
                intent.intent,
                intent.reason or "",
                float(extraction.cost_usd),
                float(extraction.extraction_time_ms),
                filename_hint,
                classification_method,
                bool(pii_redaction),
            )

        logger.info(
            "doc_recognition_run.inserted",
            run_id=str(run_id),
            tenant_id=tenant_id,
            doc_type=match.doc_type,
            intent=intent.intent,
            classification_method=classification_method,
            pii_redacted=pii_redaction,
        )
        return run_id

    async def list_runs(
        self,
        *,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        doc_type: str | None = None,
        intent: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent runs for ``tenant_id``, newest first."""
        clauses = ["tenant_id = $1"]
        params: list[Any] = [tenant_id]
        idx = 2
        if doc_type is not None:
            clauses.append(f"doc_type = ${idx}")
            params.append(doc_type)
            idx += 1
        if intent is not None:
            clauses.append(f"intent = ${idx}")
            params.append(intent)
            idx += 1
        params.append(int(limit))
        params.append(int(offset))
        sql = f"""
            SELECT id, tenant_id, doc_type, confidence, alternatives_jsonb,
                   extracted_fields_jsonb, intent, intent_reason, cost_usd,
                   extraction_time_ms, filename_hint, classification_method,
                   pii_redacted, created_at
              FROM doc_recognition_runs
             WHERE {" AND ".join(clauses)}
             ORDER BY created_at DESC
             LIMIT ${idx} OFFSET ${idx + 1}
            """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]

    async def get_run(self, run_id: uuid.UUID, tenant_id: str) -> dict[str, Any] | None:
        """Return one run by UUID, scoped to ``tenant_id`` (cross-tenant returns None)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_id, doc_type, confidence, alternatives_jsonb,
                       extracted_fields_jsonb, intent, intent_reason, cost_usd,
                       extraction_time_ms, filename_hint, classification_method,
                       pii_redacted, created_at
                  FROM doc_recognition_runs
                 WHERE id = $1 AND tenant_id = $2
                """,
                run_id,
                tenant_id,
            )
        return dict(row) if row else None

    async def aggregate_recent_costs(self, tenant_id: str, window_h: int = 24) -> dict[str, Any]:
        """Return small {total_runs, total_cost_usd, avg_extraction_ms} dict."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS total_runs,
                       COALESCE(SUM(cost_usd), 0) AS total_cost_usd,
                       COALESCE(AVG(extraction_time_ms), 0) AS avg_extraction_ms
                  FROM doc_recognition_runs
                 WHERE tenant_id = $1
                   AND created_at >= NOW() - ($2 || ' hours')::interval
                """,
                tenant_id,
                str(window_h),
            )
        if row is None:
            return {"total_runs": 0, "total_cost_usd": 0.0, "avg_extraction_ms": 0.0}
        return {
            "total_runs": int(row["total_runs"] or 0),
            "total_cost_usd": float(row["total_cost_usd"] or 0.0),
            "avg_extraction_ms": float(row["avg_extraction_ms"] or 0.0),
        }
