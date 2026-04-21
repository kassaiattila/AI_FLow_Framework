"""Add pii_redaction_reports table for PIIRedactionGate provenance.

Revision ID: 039
Revises: 038
Create Date: 2026-04-30

Sprint I / UC1 session 3 (v1.4.5.3 / S96).

Adds:
- pii_redaction_reports: per-extraction PII redaction summary emitted by
  PIIRedactionGate v0. Match spans are stored as JSONB; extraction_id is
  nullable while the gate is still unwired (S97 wires it into the
  DocumentExtractorService LLM hop).

Zero-downtime: all columns either NOT NULL with a server default or
nullable, no backfill. Downgrade is a clean DROP.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "039"
down_revision: str | None = "038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pii_redaction_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("extraction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "match_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "matches",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pii_redaction_extraction",
        "pii_redaction_reports",
        ["extraction_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pii_redaction_extraction",
        table_name="pii_redaction_reports",
    )
    op.drop_table("pii_redaction_reports")
