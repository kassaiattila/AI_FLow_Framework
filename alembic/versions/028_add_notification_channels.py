"""Add notification_channels, notification_log, in_app_notifications tables.

Revision ID: 028
Revises: 027
Create Date: 2026-04-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. notification_channels — channel configurations (SMTP, Slack, webhook, etc.)
    op.create_table(
        "notification_channels",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "channel_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_nc_channel_type", "notification_channels", ["channel_type"])
    op.create_index("idx_nc_enabled", "notification_channels", ["enabled"])
    op.create_index("idx_nc_team_id", "notification_channels", ["team_id"])

    # 2. notification_log — audit trail for every send attempt
    op.create_table(
        "notification_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "channel_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notification_channels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(500), nullable=False),
        sa.Column("template_name", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "pipeline_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_nl_channel_id", "notification_log", ["channel_id"])
    op.create_index("idx_nl_status", "notification_log", ["status"])
    op.create_index("idx_nl_sent_at", "notification_log", ["sent_at"])
    op.create_index("idx_nl_pipeline_run_id", "notification_log", ["pipeline_run_id"])

    # 3. in_app_notifications — user-facing notifications in the admin UI
    op.create_table(
        "in_app_notifications",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("read", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_ian_user_id", "in_app_notifications", ["user_id"])
    op.create_index("idx_ian_read", "in_app_notifications", ["read"])
    op.create_index("idx_ian_created_at", "in_app_notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_ian_created_at", table_name="in_app_notifications")
    op.drop_index("idx_ian_read", table_name="in_app_notifications")
    op.drop_index("idx_ian_user_id", table_name="in_app_notifications")
    op.drop_table("in_app_notifications")

    op.drop_index("idx_nl_pipeline_run_id", table_name="notification_log")
    op.drop_index("idx_nl_sent_at", table_name="notification_log")
    op.drop_index("idx_nl_status", table_name="notification_log")
    op.drop_index("idx_nl_channel_id", table_name="notification_log")
    op.drop_table("notification_log")

    op.drop_index("idx_nc_team_id", table_name="notification_channels")
    op.drop_index("idx_nc_enabled", table_name="notification_channels")
    op.drop_index("idx_nc_channel_type", table_name="notification_channels")
    op.drop_table("notification_channels")
