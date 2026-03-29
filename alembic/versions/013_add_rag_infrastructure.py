"""Add RAG infrastructure tables.

Revision ID: 013
Revises: 012
Create Date: 2026-03-29

Adds:
- rag_chunks: vector store for RAG content (if not exists from manual creation)
- rag_collections: collection config and stats
- rag_query_log: query analytics and monitoring
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # rag_chunks - may already exist from manual SQL, use IF NOT EXISTS
    op.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id TEXT PRIMARY KEY,
            collection TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB DEFAULT '{}',
            skill_name TEXT DEFAULT '',
            document_name TEXT DEFAULT '',
            chunk_index INT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_collection ON rag_chunks(collection)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_skill ON rag_chunks(skill_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_document ON rag_chunks(document_name)")

    # rag_collections - collection config and statistics
    op.create_table(
        "rag_collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("customer", sa.String(100), nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("document_count", sa.Integer, server_default="0"),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("last_ingest_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_rag_collections_customer", "rag_collections", ["customer"])
    op.create_index("idx_rag_collections_skill", "rag_collections", ["skill_name"])

    # rag_query_log - query analytics
    op.create_table(
        "rag_query_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("collection", sa.Text, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("rewritten_query", sa.Text),
        sa.Column("answer", sa.Text),
        sa.Column("sources_count", sa.Integer, server_default="0"),
        sa.Column("hallucination_score", sa.Float),
        sa.Column("response_time_ms", sa.Float),
        sa.Column("cost_usd", sa.Float, server_default="0"),
        sa.Column("role", sa.String(50), server_default="'baseline'"),
        sa.Column("customer", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_rag_query_log_collection", "rag_query_log", ["collection"])
    op.create_index("idx_rag_query_log_created", "rag_query_log", [sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("rag_query_log")
    op.drop_table("rag_collections")
    # Don't drop rag_chunks - may contain data
