"""Add human review queue table for F4d.

Revision ID: 022
Revises: 021
Create Date: 2026-04-02

Adds:
- human_review_queue: approval/rejection queue for AI-generated results
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "human_review_queue",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("reviewer", sa.String(255), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_human_review_queue_status", "human_review_queue", ["status"])
    op.create_index("ix_human_review_queue_entity", "human_review_queue", ["entity_type", "entity_id"])
    op.create_index("ix_human_review_queue_created_at", "human_review_queue", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_human_review_queue_created_at")
    op.drop_index("ix_human_review_queue_entity")
    op.drop_index("ix_human_review_queue_status")
    op.drop_table("human_review_queue")
