"""Extend rag_collections for F3 RAG Engine generalization.

Revision ID: 018
Revises: 017
Create Date: 2026-04-01

Adds:
- rag_collections: description, language, embedding_model columns
- rag_query_log: collection_id FK to rag_collections
- rag_feedback: standalone feedback table for query ratings
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend rag_collections with F3 fields
    op.add_column("rag_collections", sa.Column("description", sa.Text))
    op.add_column("rag_collections", sa.Column("language", sa.String(10), server_default="'hu'"))
    op.add_column("rag_collections", sa.Column("embedding_model", sa.String(255),
                                                server_default="'openai/text-embedding-3-small'"))

    # Add collection_id FK to rag_query_log (nullable for backward compat)
    op.add_column("rag_query_log", sa.Column(
        "collection_id", UUID(as_uuid=True), nullable=True,
    ))
    op.create_foreign_key(
        "fk_rag_query_log_collection_id",
        "rag_query_log", "rag_collections",
        ["collection_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_rag_query_log_collection_id", "rag_query_log", ["collection_id"])

    # rag_feedback — standalone feedback table
    op.create_table(
        "rag_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("query_id", UUID(as_uuid=True), nullable=True),
        sa.Column("collection_id", UUID(as_uuid=True), nullable=True),
        sa.Column("thumbs_up", sa.Boolean, nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["query_id"], ["rag_query_log.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["collection_id"], ["rag_collections.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_rag_feedback_collection", "rag_feedback", ["collection_id"])
    op.create_index("idx_rag_feedback_query", "rag_feedback", ["query_id"])
    op.create_index("idx_rag_feedback_created", "rag_feedback", [sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("rag_feedback")
    op.drop_index("idx_rag_query_log_collection_id", "rag_query_log")
    op.drop_constraint("fk_rag_query_log_collection_id", "rag_query_log", type_="foreignkey")
    op.drop_column("rag_query_log", "collection_id")
    op.drop_column("rag_collections", "embedding_model")
    op.drop_column("rag_collections", "language")
    op.drop_column("rag_collections", "description")
