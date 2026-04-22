"""Add embedding_decisions table for EmbeddingDecision persistence.

Revision ID: 040
Revises: 039
Create Date: 2026-04-22

Sprint J / UC2 session 1 (v1.4.6 / S100).

Adds:
- embedding_decisions: per-tenant policy output naming which embedder
  profile (A = BGE-M3, B = Azure OpenAI) and concrete model produced a
  chunk batch's vectors. Attached downstream by the RAG ingest step
  (S101+) so that pgvector rows can be traced back to a decision.

Zero-downtime: every column is NOT NULL with a server default or is part
of the primary key. No backfill. Downgrade is a clean DROP TABLE.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "040"
down_revision: str | None = "039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "embedding_decisions",
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column(
            "profile",
            sa.CHAR(length=1),
            nullable=False,
        ),
        sa.Column(
            "tenant_override_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "decision_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "profile IN ('A','B')",
            name="ck_embedding_decisions_profile",
        ),
    )
    op.create_index(
        "ix_embedding_decisions_tenant",
        "embedding_decisions",
        ["tenant_id", sa.text("decision_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_embedding_decisions_tenant",
        table_name="embedding_decisions",
    )
    op.drop_table("embedding_decisions")
