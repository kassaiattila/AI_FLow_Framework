"""Add RPA browser automation tables for F4c.

Revision ID: 021
Revises: 020
Create Date: 2026-04-02

Adds:
- rpa_configs: YAML-based browser automation configurations
- rpa_execution_log: execution history per config run
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rpa_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("yaml_config", sa.Text(), nullable=False),
        sa.Column("target_url", sa.String(2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rpa_execution_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("config_id", sa.String(36), sa.ForeignKey("rpa_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("steps_total", sa.Integer(), nullable=True),
        sa.Column("steps_completed", sa.Integer(), server_default="0"),
        sa.Column("results", JSONB, nullable=True),
        sa.Column("screenshots", JSONB, nullable=True, server_default="[]"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rpa_execution_log_config_id", "rpa_execution_log", ["config_id"])
    op.create_index("ix_rpa_execution_log_started_at", "rpa_execution_log", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_rpa_execution_log_started_at")
    op.drop_index("ix_rpa_execution_log_config_id")
    op.drop_table("rpa_execution_log")
    op.drop_table("rpa_configs")
