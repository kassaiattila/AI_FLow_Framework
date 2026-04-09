"""Add generated_specs table for B5.2 Spec Writer skill persistence.

Revision ID: 030
Revises: 029
Create Date: 2026-04-09

Adds:
- generated_specs: stores LLM-generated Markdown specifications with metadata
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "030"
down_revision: str | None = "029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_specs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("spec_type", sa.String(50), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("title", sa.String(512), nullable=False, server_default=""),
        sa.Column("markdown_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("requirement", JSONB, nullable=True),
        sa.Column("review", JSONB, nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("is_acceptable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sections_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_generated_specs_created_at", "generated_specs", ["created_at"])
    op.create_index("ix_generated_specs_spec_type", "generated_specs", ["spec_type"])


def downgrade() -> None:
    op.drop_index("ix_generated_specs_spec_type")
    op.drop_index("ix_generated_specs_created_at")
    op.drop_table("generated_specs")
