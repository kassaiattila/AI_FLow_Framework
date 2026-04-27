"""Sprint X / SX-3 — routing_runs audit + observability table.

Revision ID: 050
Revises: 049
Create Date: 2026-04-27

Persistence boundary for the UC3 EXTRACT routing decision (Sprint X / SX-2
landed the dispatch in :mod:`aiflow.services.email_connector.orchestrator`;
SX-3 makes it observable). One row per EXTRACT email regardless of which
dispatch path ran:

* ``invoice_processor`` — Sprint Q / S135 byte-stable path (flag-off, or
  flag-on ``hu_invoice`` doctype, or fallback policy).
* ``doc_recognizer_workflow`` — DocRecognizer's PromptWorkflow extractor
  (Sprint W SW-1) for non-invoice doctypes.
* ``rag_ingest_fallback`` — RAG handoff for unknown doctypes (placeholder
  in SX-2; full handoff is later Sprint).
* ``skipped`` — confidence below threshold + policy says skip.

Columns:

* ``id`` — UUID primary key.
* ``tenant_id`` — multi-tenant attribution.
* ``email_id`` — UUID of the originating email (= ``workflow_runs.id``;
  no foreign key because emails are surfaced via workflow_runs in this
  codebase, no separate ``emails`` table). Nullable so a write failure
  on lookup never poisons the audit row.
* ``intent_class`` — abstract class from the v1 intent schema (EXTRACT
  for every row written by the SX-3 hook; field is populated for forward
  compatibility when other intent classes start emitting trails).
* ``doctype_detected`` + ``doctype_confidence`` — top-1 doctype the
  router observed across the email's attachments (``NULL`` on the
  flag-off / no-routing path).
* ``extraction_path`` — which downstream handler ran.
* ``extraction_outcome`` — aggregated per-email outcome (single-attachment
  emails map 1:1; multi-attachment emails collapse to ``success`` /
  ``partial`` / ``failed`` / ``refused_cost`` / ``skipped``).
* ``cost_usd`` + ``latency_ms`` — observability totals.
* ``metadata`` — per-attachment detail (capped 8 KB at write-time;
  truncation logged WARN). Mirrors
  :class:`UC3ExtractRouting.attachments` shape but with PII-redacted
  filenames + extracted-field values.
* ``created_at`` — server-side timestamp.

Indexes optimize the typical operator queries:

* ``(tenant_id, created_at DESC)`` — per-tenant runs board.
* ``(email_id)`` — email-detail deep-link.
* ``(extraction_outcome)`` — outcome-distribution aggregation for
  ``GET /api/v1/routing-runs/stats``.

Idempotent + reversible:

* Upgrade creates the table + 3 indexes.
* Downgrade drops everything in reverse order.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routing_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("email_id", UUID(as_uuid=True), nullable=True),
        sa.Column("intent_class", sa.Text(), nullable=False),
        sa.Column("doctype_detected", sa.Text(), nullable=True),
        sa.Column("doctype_confidence", sa.Float(), nullable=True),
        sa.Column("extraction_path", sa.Text(), nullable=False),
        sa.Column("extraction_outcome", sa.Text(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "extraction_path IN ('invoice_processor','doc_recognizer_workflow',"
            "'rag_ingest_fallback','skipped')",
            name="ck_routing_runs_extraction_path_enum",
        ),
        sa.CheckConstraint(
            "extraction_outcome IN ('success','partial','failed','refused_cost','skipped')",
            name="ck_routing_runs_extraction_outcome_enum",
        ),
        sa.CheckConstraint(
            "doctype_confidence IS NULL OR (doctype_confidence >= 0 AND doctype_confidence <= 1)",
            name="ck_routing_runs_doctype_confidence_range",
        ),
        sa.CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="ck_routing_runs_cost_nonneg",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_routing_runs_latency_nonneg",
        ),
    )
    op.create_index(
        "ix_routing_runs_tenant_created",
        "routing_runs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_routing_runs_email_id",
        "routing_runs",
        ["email_id"],
    )
    op.create_index(
        "ix_routing_runs_extraction_outcome",
        "routing_runs",
        ["extraction_outcome"],
    )


def downgrade() -> None:
    op.drop_index("ix_routing_runs_extraction_outcome", table_name="routing_runs")
    op.drop_index("ix_routing_runs_email_id", table_name="routing_runs")
    op.drop_index("ix_routing_runs_tenant_created", table_name="routing_runs")
    op.drop_table("routing_runs")
