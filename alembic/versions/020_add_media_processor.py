"""Add media processing tables for F4b Media Processor.

Revision ID: 020
Revises: 019
Create Date: 2026-04-02

Adds:
- media_jobs: tracks media processing jobs (upload → STT → structure)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("media_type", sa.String(50), nullable=False, server_default="video"),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("stt_provider", sa.String(100), nullable=False, server_default="whisper"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("transcript_raw", sa.Text(), nullable=True),
        sa.Column("transcript_structured", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=True, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("processing_time_ms", sa.Float(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_media_jobs_status", "media_jobs", ["status"])
    op.create_index("ix_media_jobs_created_at", "media_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_media_jobs_created_at")
    op.drop_index("ix_media_jobs_status")
    op.drop_table("media_jobs")
