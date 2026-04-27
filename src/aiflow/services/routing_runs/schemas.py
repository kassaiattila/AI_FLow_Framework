"""Pydantic v2 schemas for the routing_runs audit table.

Five external types feed the SX-3 surface:

* :class:`RoutingRunCreate` — write envelope used by the orchestrator
  hook. Carries only the columns the writer is responsible for; the
  generated ``id`` and server-default ``created_at`` are server-side.
* :class:`RoutingRunSummary` — list-row shape returned by
  ``GET /api/v1/routing-runs/`` (one record per row, no full ``metadata``
  payload — keeps list responses cheap).
* :class:`RoutingRunDetail` — single-row shape returned by
  ``GET /api/v1/routing-runs/{id}`` including the full ``metadata``
  JSONB.
* :class:`RoutingRunFilters` — query filters envelope.
* :class:`RoutingStatsResponse` — aggregate envelope returned by
  ``GET /api/v1/routing-runs/stats`` (per-doctype + per-outcome
  distributions + cost/latency centiles).

The two helper functions :func:`aggregate_outcome` and
:func:`summarize_routing_decision` convert a Sprint X / SX-2
:class:`UC3ExtractRouting` payload into the table-shaped fields the
writer needs. They are pure, sync, and trivially unit-testable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ExtractionOutcomeAggregated",
    "ExtractionPathLiteral",
    "RoutingRunCreate",
    "RoutingRunDetail",
    "RoutingRunFilters",
    "RoutingRunSummary",
    "RoutingStatsBucket",
    "RoutingStatsResponse",
    "aggregate_outcome",
    "summarize_routing_decision",
]


ExtractionPathLiteral = Literal[
    "invoice_processor",
    "doc_recognizer_workflow",
    "rag_ingest_fallback",
    "skipped",
]
"""Mirrors the CHECK constraint on ``routing_runs.extraction_path``.

Note the ``rag_ingest_fallback`` spelling — the SX-2 contract uses
``rag_ingest`` but the audit table uses the more explicit
``rag_ingest_fallback`` to make the policy origin obvious to operators
reading the table directly.
"""

ExtractionOutcomeAggregated = Literal[
    "success",
    "partial",
    "failed",
    "refused_cost",
    "skipped",
]
"""Mirrors the CHECK constraint on ``routing_runs.extraction_outcome``.

Per-attachment outcomes from the SX-2 contract collapse to these five
values via :func:`aggregate_outcome`. Single-attachment emails map 1:1
(``succeeded`` → ``success``, ``timed_out`` → ``failed``); multi-
attachment emails collapse via the rules documented on that helper.
"""


class RoutingRunCreate(BaseModel):
    """Write envelope — orchestrator hook builds this then calls
    :meth:`RoutingRunRepository.insert`."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(..., min_length=1)
    email_id: UUID | None = Field(default=None)
    intent_class: str = Field(..., min_length=1)
    doctype_detected: str | None = Field(default=None)
    doctype_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    extraction_path: ExtractionPathLiteral
    extraction_outcome: ExtractionOutcomeAggregated
    cost_usd: float | None = Field(default=None, ge=0.0)
    latency_ms: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = Field(default=None)


class RoutingRunSummary(BaseModel):
    """List-row shape — returned by GET /api/v1/routing-runs/."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: str
    email_id: UUID | None
    intent_class: str
    doctype_detected: str | None
    doctype_confidence: float | None
    extraction_path: ExtractionPathLiteral
    extraction_outcome: ExtractionOutcomeAggregated
    cost_usd: float | None
    latency_ms: int | None
    created_at: datetime


class RoutingRunDetail(RoutingRunSummary):
    """Single-row shape including the full metadata JSONB."""

    metadata: dict[str, Any] | None = None
    metadata_truncated: bool = False
    metadata_truncated_count: int = 0


class RoutingRunFilters(BaseModel):
    """Query envelope for the list route."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    intent_class: str | None = None
    doctype_detected: str | None = None
    extraction_outcome: ExtractionOutcomeAggregated | None = None
    since: datetime | None = None
    until: datetime | None = None


class RoutingStatsBucket(BaseModel):
    """Single bucket inside a distribution map."""

    model_config = ConfigDict(extra="forbid")

    key: str
    count: int = Field(..., ge=0)


class RoutingStatsResponse(BaseModel):
    """Aggregate response for GET /api/v1/routing-runs/stats."""

    model_config = ConfigDict(extra="forbid")

    since: datetime
    until: datetime
    total_runs: int = Field(..., ge=0)
    by_doctype: list[RoutingStatsBucket] = Field(default_factory=list)
    by_outcome: list[RoutingStatsBucket] = Field(default_factory=list)
    by_extraction_path: list[RoutingStatsBucket] = Field(default_factory=list)
    mean_cost_usd: float = Field(default=0.0, ge=0.0)
    p50_latency_ms: float = Field(default=0.0, ge=0.0)
    p95_latency_ms: float = Field(default=0.0, ge=0.0)


# ---------------------------------------------------------------------------
# Aggregation helpers (pure, sync, unit-testable)
# ---------------------------------------------------------------------------


_PER_ATTACHMENT_TO_AGGREGATE: dict[str, ExtractionOutcomeAggregated] = {
    "succeeded": "success",
    "failed": "failed",
    "timed_out": "failed",
    "refused_cost": "refused_cost",
    "skipped": "skipped",
}


def aggregate_outcome(
    per_attachment_outcomes: list[str],
) -> ExtractionOutcomeAggregated:
    """Collapse the per-attachment outcomes (SX-2 contract) into the
    five aggregate values the audit table CHECK constraint accepts.

    Rules:

    * Empty list → ``"skipped"`` (no extraction was run).
    * Single-attachment emails map 1:1 via the lookup table
      (``succeeded`` → ``success``, ``failed`` / ``timed_out`` →
      ``failed``, etc.).
    * Multi-attachment emails:

      * any ``"succeeded"`` AND any non-success → ``"partial"``
      * all ``"succeeded"`` → ``"success"``
      * all ``"refused_cost"`` → ``"refused_cost"``
      * all ``"skipped"`` → ``"skipped"``
      * everything else (including all ``"failed"`` / ``"timed_out"``,
        or a mix without any success) → ``"failed"``

    Unknown per-attachment outcomes are treated as ``"failed"`` so a
    contract drift never produces a CHECK-violating insert.
    """
    if not per_attachment_outcomes:
        return "skipped"

    aggregates = [_PER_ATTACHMENT_TO_AGGREGATE.get(o, "failed") for o in per_attachment_outcomes]

    if len(aggregates) == 1:
        return aggregates[0]

    has_success = any(a == "success" for a in aggregates)
    all_success = all(a == "success" for a in aggregates)
    all_refused = all(a == "refused_cost" for a in aggregates)
    all_skipped = all(a == "skipped" for a in aggregates)

    if all_success:
        return "success"
    if has_success:
        return "partial"
    if all_refused:
        return "refused_cost"
    if all_skipped:
        return "skipped"
    return "failed"


def summarize_routing_decision(
    routing_decision: dict[str, Any],
) -> tuple[str | None, float | None, ExtractionPathLiteral, ExtractionOutcomeAggregated]:
    """Pull (doctype, confidence, path, outcome) out of an SX-2
    :class:`UC3ExtractRouting` JSON dump.

    Tactic for the four fields:

    * ``doctype_detected`` — first attachment that has a non-None
      ``doctype_detected`` (the SX-2 contract preserves attachment order
      so this is deterministic; multi-attachment emails with multiple
      doctypes are summarised as the first observed; the full per-
      attachment breakdown is in ``metadata``).
    * ``doctype_confidence`` — the same attachment's confidence.
    * ``extraction_path`` — the path of the FIRST attachment whose
      outcome was not ``"skipped"`` (so the operator-visible path
      reflects what actually ran). Falls back to first-attachment-wins
      when every attachment was skipped. The SX-2 ``"rag_ingest"``
      spelling is mapped to the audit-table spelling
      ``"rag_ingest_fallback"``.
    * ``extraction_outcome`` — :func:`aggregate_outcome` over
      per-attachment outcomes.
    """
    attachments = routing_decision.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = []

    doctype: str | None = None
    confidence: float | None = None
    for att in attachments:
        if not isinstance(att, dict):
            continue
        d = att.get("doctype_detected")
        if d:
            doctype = d
            raw_conf = att.get("doctype_confidence")
            try:
                confidence = float(raw_conf) if raw_conf is not None else None
            except (TypeError, ValueError):
                confidence = None
            break

    path: ExtractionPathLiteral = "skipped"
    chosen = next(
        (
            a
            for a in attachments
            if isinstance(a, dict) and a.get("extraction_outcome") not in (None, "skipped")
        ),
        None,
    )
    if chosen is None and attachments:
        first = attachments[0]
        if isinstance(first, dict):
            chosen = first
    if chosen is not None:
        raw_path = chosen.get("extraction_path") or "skipped"
        path = _normalize_extraction_path(raw_path)

    outcomes = [
        att.get("extraction_outcome", "failed") for att in attachments if isinstance(att, dict)
    ]
    outcome = aggregate_outcome(outcomes)

    return doctype, confidence, path, outcome


def _normalize_extraction_path(raw: str) -> ExtractionPathLiteral:
    """Map the SX-2 contract spelling onto the audit-table CHECK enum."""
    if raw == "rag_ingest":
        return "rag_ingest_fallback"
    if raw in ("invoice_processor", "doc_recognizer_workflow", "skipped"):
        return raw  # type: ignore[return-value]
    if raw == "rag_ingest_fallback":
        return "rag_ingest_fallback"
    return "skipped"
