"""Add scheduling tables.

Revision ID: 007
Revises: 006
Create Date: 2026-03-28

Adds:
- schedules: cron / event / webhook trigger definitions
- Indexes: team_id, enabled
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- schedules table ---
    op.create_table(
        "schedules",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("workflow_name", sa.String(255), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("cron_expression", sa.String(100)),
        sa.Column("event_pattern", sa.String(500)),
        sa.Column("webhook_path", sa.String(500)),
        sa.Column("input_data", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("priority", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_status", sa.String(50)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("run_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- indexes ---
    op.create_index(
        "idx_schedules_team_id",
        "schedules",
        ["team_id"],
    )
    op.create_index(
        "idx_schedules_enabled",
        "schedules",
        ["enabled"],
    )


def downgrade() -> None:
    op.drop_table("schedules")
