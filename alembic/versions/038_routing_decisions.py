"""Add routing_decisions table for RoutingDecision persistence.

Revision ID: 038
Revises: 037
Create Date: 2026-04-30

Sprint I / UC1 session 2 (v1.4.5.2 / S95).

Adds:
- routing_decisions: per-file router output (chosen_parser, signals,
  fallback_chain) emitted by MultiSignalRouter.decide().

Zero-downtime: every column is either NOT NULL with a server default, or
nullable. No backfill. Downgrade is a clean DROP TABLE.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "038"
down_revision: str | None = "037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "routing_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("chosen_parser", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "signals",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "fallback_chain",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "cost_estimate",
            sa.Numeric(10, 6),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "decided_at",
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
    )
    op.create_index(
        "ix_routing_decisions_package",
        "routing_decisions",
        ["package_id"],
    )
    op.create_index(
        "ix_routing_decisions_tenant",
        "routing_decisions",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_routing_decisions_tenant", table_name="routing_decisions")
    op.drop_index("ix_routing_decisions_package", table_name="routing_decisions")
    op.drop_table("routing_decisions")
