"""Add email_connector_configs and email_fetch_history tables.

Revision ID: 017
Revises: 016
Create Date: 2026-04-01

Adds:
- email_connector_configs: email connector configuration (IMAP, O365/Graph, Gmail)
- email_fetch_history: tracks each email fetch operation per connector
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- email_connector_configs ---
    op.create_table(
        "email_connector_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("host", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer, nullable=True),
        sa.Column("use_ssl", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("mailbox", sa.String(255), nullable=True),
        sa.Column("credentials_encrypted", sa.Text, nullable=True),
        sa.Column("filters", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("polling_interval_minutes", sa.Integer, server_default=sa.text("15"), nullable=False),
        sa.Column("max_emails_per_fetch", sa.Integer, server_default=sa.text("50"), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "provider IN ('imap', 'o365_graph', 'gmail')",
            name="chk_ecc_provider",
        ),
    )
    op.create_index("idx_ecc_provider", "email_connector_configs", ["provider"])
    op.create_index("idx_ecc_is_active", "email_connector_configs", ["is_active"])
    op.create_index("idx_ecc_name", "email_connector_configs", ["name"], unique=True)

    # --- email_fetch_history ---
    op.create_table(
        "email_fetch_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "config_id",
            UUID(as_uuid=True),
            sa.ForeignKey("email_connector_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("email_count", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("new_emails", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="chk_efh_status",
        ),
    )
    op.create_index("idx_efh_config_id", "email_fetch_history", ["config_id"])
    op.create_index("idx_efh_fetched_at", "email_fetch_history", ["fetched_at"])
    op.create_index("idx_efh_status", "email_fetch_history", ["status"])


def downgrade() -> None:
    op.drop_table("email_fetch_history")
    op.drop_table("email_connector_configs")
