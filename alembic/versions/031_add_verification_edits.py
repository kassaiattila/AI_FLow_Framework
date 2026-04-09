"""Add verification_edits table for B7 Verification Page v2 diff persistence.

Revision ID: 031
Revises: 030
Create Date: 2026-04-11

Adds:
- verification_edits: stores per-field edit diffs with audit trail
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "031"
down_revision: str | None = "030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "verification_edits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("field_name", sa.String(255), nullable=False),
        sa.Column("field_category", sa.String(100), nullable=True),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("edited_value", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("editor_user_id", sa.String(36), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_verification_edits_document",
        "verification_edits",
        ["document_id"],
    )
    op.create_index(
        "idx_verification_edits_status",
        "verification_edits",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("idx_verification_edits_status")
    op.drop_index("idx_verification_edits_document")
    op.drop_table("verification_edits")
