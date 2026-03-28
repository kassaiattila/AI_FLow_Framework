"""Add vector store tables: collections, documents, chunks, document_sync_schedules.

Revision ID: 004
Revises: 003
Create Date: 2026-03-28

Note: Requires pgvector extension. Run: CREATE EXTENSION IF NOT EXISTS vector;
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("embedding_model_id", UUID(as_uuid=True), sa.ForeignKey("embedding_models.id", ondelete="SET NULL")),
        sa.Column("document_count", sa.Integer, server_default="0"),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("is_shared", sa.Boolean, server_default="false"),
        sa.Column("chunking_config", JSONB, server_default="{}"),
        sa.Column("search_config", JSONB, server_default="{}"),
        sa.Column("team_id", UUID(as_uuid=True)),  # FK added in migration 005
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("name", "skill_name", name="uq_collection_skill"),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_hash_sha256", sa.String(64), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("department", sa.String(100)),
        sa.Column("language", sa.String(10), server_default="hu"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_until", sa.Date),
        sa.Column("version_number", sa.Integer, server_default="1"),
        sa.Column("supersedes_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("collection_name", sa.String(255), nullable=False),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("embedding_model", sa.String(100)),
        sa.Column("ingestion_status", sa.String(20), server_default="pending"),
        sa.Column("source_type", sa.String(50)),
        sa.Column("source_uri", sa.Text),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_doc_skill", "documents", ["skill_name", "collection_name"])
    op.create_index("idx_doc_status", "documents", ["status"])
    op.create_index("idx_doc_hash", "documents", ["file_hash_sha256"])
    op.create_index("idx_doc_supersedes", "documents", ["supersedes_id"])

    # Chunks table with vector column
    op.create_table(
        "chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE")),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_start", sa.Integer),
        sa.Column("page_end", sa.Integer),
        sa.Column("section_title", sa.String(500)),
        sa.Column("section_hierarchy", JSONB),
        sa.Column("parent_chunk_id", UUID(as_uuid=True), sa.ForeignKey("chunks.id", ondelete="SET NULL")),
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("collection_name", sa.String(255), nullable=False),
        sa.Column("document_title", sa.String(500)),
        sa.Column("document_status", sa.String(20)),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_until", sa.Date),
        sa.Column("language", sa.String(10)),
        sa.Column("department", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    # Note: vector column and HNSW index added separately (pgvector-specific SQL)
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1536)")
    op.execute("ALTER TABLE chunks ADD COLUMN content_tsv tsvector")
    op.execute("CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)")
    op.execute("CREATE INDEX idx_chunks_tsv ON chunks USING GIN (content_tsv)")
    op.create_index("idx_chunks_skill_coll", "chunks", ["skill_name", "collection_name"])
    op.create_index("idx_chunks_status", "chunks", ["document_status"])
    op.create_index("idx_chunks_document_id", "chunks", ["document_id"])

    op.create_table(
        "document_sync_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("collections.id")),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_config", JSONB, nullable=False),
        sa.Column("sync_cron", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_status", sa.String(20)),
        sa.Column("last_sync_error", sa.Text),
        sa.Column("files_synced", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

def downgrade() -> None:
    op.drop_table("document_sync_schedules")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("collections")
    op.execute("DROP EXTENSION IF EXISTS vector")
