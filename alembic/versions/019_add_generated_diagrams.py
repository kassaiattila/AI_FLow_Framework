"""Add generated_diagrams table for F4a Diagram Generator persistence.

Revision ID: 019
Revises: 018
Create Date: 2026-04-01

Adds:
- generated_diagrams: stores generated BPMN/Mermaid diagrams with metadata
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generated_diagrams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("mermaid_code", sa.Text(), nullable=False, server_default=""),
        sa.Column("drawio_xml", sa.Text(), nullable=True),
        sa.Column("bpmn_xml", sa.Text(), nullable=True),
        sa.Column("svg_content", sa.Text(), nullable=True),
        sa.Column("review", JSONB, nullable=True),
        sa.Column("export_formats", JSONB, nullable=True, server_default="[]"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_generated_diagrams_created_at", "generated_diagrams", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_generated_diagrams_created_at")
    op.drop_table("generated_diagrams")
