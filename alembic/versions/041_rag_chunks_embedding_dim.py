"""Add embedding_dim column to rag_chunks for provenance.

Revision ID: 041
Revises: 040
Create Date: 2026-04-23

Sprint J / UC2 session 2 (v1.4.6 / S101).

Adds:
- rag_chunks.embedding_dim (INTEGER, NULL): records the dimensionality of
  the vector stored in the ``embedding`` column. Today the column is a
  fixed ``vector(1536)`` so this is informational only — it lets the RAG
  retrieval layer reject cross-dim comparisons once Sprint J S102 widens
  ``rag_chunks.embedding`` to support BGE-M3 (1024) alongside Azure OpenAI
  (1536).

Zero-downtime: the new column is nullable with no backfill. Existing rows
remain readable; new rows populated by ``rag_engine.ingest_documents``
when the provider-registry flow is enabled. Downgrade is a clean DROP
COLUMN.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "041"
down_revision: str | None = "040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rag_chunks",
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rag_chunks", "embedding_dim")
