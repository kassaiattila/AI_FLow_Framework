"""UC3 EXTRACT routing — Sprint X / SX-2.

Models the per-attachment dispatch decision when an EXTRACT-class email is
fanned out through :class:`DocumentRecognizerOrchestrator`. Distinct from
:mod:`aiflow.contracts.routing_decision` which captures *parser*
selection upstream; this module captures the doctype → extractor
routing decision *downstream* of classification.

Surfaces in two places:

* ``workflow_runs.output_data["routing_decision"]`` — the JSON dump of
  :class:`UC3ExtractRouting` (one record per email).
* ``EmailDetailResponse.routing_decision`` — pass-through dict for the
  admin UI ``/routing-runs`` page (Sprint X / SX-3).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "UC3AttachmentRoute",
    "UC3ExtractRouting",
    "ExtractionPath",
    "ExtractionOutcome",
]


ExtractionPath = Literal[
    "invoice_processor",
    "doc_recognizer_workflow",
    "rag_ingest",
    "skipped",
]
"""Which downstream handler ran for a given attachment.

* ``invoice_processor`` — byte-stable Sprint Q / S135 path. Used for
  ``hu_invoice`` doctype + ``unknown_doctype_action="fallback_invoice_processor"``.
* ``doc_recognizer_workflow`` — DocRecognizer's PromptWorkflow extractor
  (Sprint W SW-1) for non-invoice doctypes (id_card, address_card,
  passport, contract).
* ``rag_ingest`` — RAG knowledge-base ingestion handoff for unknown
  doctypes (placeholder behavior in SX-2; full handoff is Sprint Y).
* ``skipped`` — no extraction was run (below-threshold or
  ``unknown_doctype_action="skip"``).
"""

ExtractionOutcome = Literal[
    "succeeded",
    "failed",
    "refused_cost",
    "skipped",
    "timed_out",
]
"""Per-attachment extraction outcome.

* ``succeeded`` — extractor returned non-error result.
* ``failed`` — extractor raised; per-attachment error isolation kept the
  rest of the email moving.
* ``refused_cost`` — :class:`CostPreflightGuardrail` returned
  ``allowed=False`` (per-step ceiling). No LLM call was made.
* ``skipped`` — confidence below threshold + policy says skip, OR the
  attachment was filtered out by file/MIME pre-checks.
* ``timed_out`` — per-attachment slice of
  ``total_budget_seconds`` elapsed before the extractor returned.
"""


class UC3AttachmentRoute(BaseModel):
    """Single attachment's dispatch decision + outcome.

    The ``attachment_id`` matches ``IntakeFile.file_id`` so the admin UI
    can join back to the original file row when surfacing the routing
    trail.
    """

    model_config = ConfigDict(extra="forbid")

    attachment_id: str = Field(..., min_length=1, description="IntakeFile.file_id (string form).")
    filename: str = Field(..., description="Original attachment filename.")
    doctype_detected: str | None = Field(
        default=None,
        description=(
            "DocRecognizer's top-1 doctype name (e.g. ``hu_invoice``). "
            "``None`` when classification produced no match (registry empty, "
            "all rules zero-weighted)."
        ),
    )
    doctype_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Top-1 doctype confidence."
    )
    extraction_path: ExtractionPath = Field(
        ..., description="Which downstream handler ran (or ``skipped``)."
    )
    extraction_outcome: ExtractionOutcome = Field(
        ..., description="Result code for the dispatched handler."
    )
    cost_usd: float = Field(default=0.0, ge=0.0, description="LLM/parser USD cost.")
    latency_ms: float = Field(
        default=0.0, ge=0.0, description="Wall-clock time spent on this attachment."
    )
    error: str | None = Field(
        default=None,
        max_length=500,
        description="Short error class + message when ``extraction_outcome != 'succeeded'``.",
    )


class UC3ExtractRouting(BaseModel):
    """Per-email routing trail — one record per scan-and-classify run.

    Lives in ``workflow_runs.output_data["routing_decision"]`` and is
    copied through to ``EmailDetailResponse.routing_decision`` so the
    admin UI can surface the dispatch decision without re-running
    classification.
    """

    model_config = ConfigDict(extra="forbid")

    attachments: list[UC3AttachmentRoute] = Field(default_factory=list)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    total_latency_ms: float = Field(default=0.0, ge=0.0)
    confidence_threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Threshold value used for this run."
    )
    unknown_doctype_action: Literal["fallback_invoice_processor", "rag_ingest", "skip"] = Field(
        ..., description="Policy applied when a doctype was below threshold."
    )
