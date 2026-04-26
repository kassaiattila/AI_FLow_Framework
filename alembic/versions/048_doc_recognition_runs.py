"""Sprint V SV-3 — doc_recognition_runs audit + observability table.

Revision ID: 048
Revises: 047
Create Date: 2026-04-26

Persistence boundary for the document recognizer skill. Each call to
``recognize_and_extract`` writes one row capturing:

* ``tenant_id`` — multi-tenant attribution
* ``doc_type`` + ``confidence`` + ``alternatives_jsonb`` — classifier output
* ``extracted_fields_jsonb`` — values + per-field confidence (PII redacted
  at the audit-log boundary when the descriptor's
  ``intent_routing.pii_redaction`` is True)
* ``intent`` + ``intent_reason`` — routing decision
* ``cost_usd`` + ``extraction_time_ms`` — observability
* ``filename_hint`` — original filename (for forensic correlation, no PII)
* ``classification_method`` — ``rule_engine`` / ``llm_fallback`` / ``hint``
* ``created_at`` — server-side timestamp

Indexes optimize the typical operator queries:
* ``(tenant_id, created_at DESC)`` — per-tenant runs board (newest first)
* ``(doc_type, created_at DESC)`` — per-doctype accuracy spot-checks
* ``(intent, tenant_id)`` — routing-board (route_to_human queue)

Idempotent + reversible:
- Upgrade creates the table + 3 indexes.
- Downgrade drops everything in reverse order.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doc_recognition_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "alternatives_jsonb",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "extracted_fields_jsonb",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("intent_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("extraction_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("filename_hint", sa.Text(), nullable=True),
        sa.Column("classification_method", sa.Text(), nullable=False, server_default="rule_engine"),
        sa.Column("pii_redacted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_doc_recognition_runs_confidence_range"
        ),
        sa.CheckConstraint("cost_usd >= 0", name="ck_doc_recognition_runs_cost_nonneg"),
        sa.CheckConstraint(
            "intent IN ('process','route_to_human','rag_ingest','respond','reject')",
            name="ck_doc_recognition_runs_intent_enum",
        ),
        sa.CheckConstraint(
            "classification_method IN ('rule_engine','llm_fallback','hint')",
            name="ck_doc_recognition_runs_method_enum",
        ),
    )
    op.create_index(
        "ix_doc_recognition_runs_tenant_created",
        "doc_recognition_runs",
        ["tenant_id", "created_at"],
        postgresql_using="btree",
        # NOTE: alembic op.create_index doesn't accept `postgresql_ops` here cleanly across
        # versions; the DESC ordering for ``created_at`` is achieved at query-time.
    )
    op.create_index(
        "ix_doc_recognition_runs_doctype_created",
        "doc_recognition_runs",
        ["doc_type", "created_at"],
    )
    op.create_index(
        "ix_doc_recognition_runs_intent_tenant",
        "doc_recognition_runs",
        ["intent", "tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_doc_recognition_runs_intent_tenant", table_name="doc_recognition_runs")
    op.drop_index("ix_doc_recognition_runs_doctype_created", table_name="doc_recognition_runs")
    op.drop_index("ix_doc_recognition_runs_tenant_created", table_name="doc_recognition_runs")
    op.drop_table("doc_recognition_runs")
