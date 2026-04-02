"""Add api_keys table for F5c admin key management.

Revision ID: 024
Revises: 023
Create Date: 2026-04-02

Adds:
- api_keys: named API keys with hash, prefix, optional user binding
"""

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_api_keys_prefix", "api_keys", ["prefix"], unique=True)
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_is_active", "api_keys", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_api_keys_is_active")
    op.drop_index("idx_api_keys_user_id")
    op.drop_index("idx_api_keys_prefix")
    op.drop_table("api_keys")
