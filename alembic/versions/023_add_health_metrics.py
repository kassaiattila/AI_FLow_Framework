"""Add health metrics and audit tables for F5.

Revision ID: 023
Revises: 022
Create Date: 2026-04-02

Adds:
- service_health_log: periodic health check results per service
- audit_log: immutable audit trail for all API operations
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing_tables = insp.get_table_names()

    if "service_health_log" not in existing_tables:
        op.create_table(
            "service_health_log",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("service_name", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("details", JSONB, nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_service_health_log_service", "service_health_log", ["service_name"])
        op.create_index("ix_service_health_log_checked_at", "service_health_log", ["checked_at"])

    if "audit_log" not in existing_tables:
        op.create_table(
            "audit_log",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("entity_type", sa.String(100), nullable=False),
            sa.Column("entity_id", sa.String(36), nullable=True),
            sa.Column("user_id", sa.String(255), nullable=True),
            sa.Column("details", JSONB, nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_audit_log_action", "audit_log", ["action"])
        op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
        op.create_index("ix_audit_log_user", "audit_log", ["user_id"])
        op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_created_at")
    op.drop_index("ix_audit_log_user")
    op.drop_index("ix_audit_log_entity")
    op.drop_index("ix_audit_log_action")
    op.drop_table("audit_log")
    op.drop_index("ix_service_health_log_checked_at")
    op.drop_index("ix_service_health_log_service")
    op.drop_table("service_health_log")
