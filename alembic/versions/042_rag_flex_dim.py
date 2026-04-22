"""pgvector flex-dim + rag_collections.embedding_dim (Strategy B).

Revision ID: 042
Revises: 041
Create Date: 2026-04-25

Sprint J / UC2 session 4 (v1.4.6 / S103).

Problem: ``rag_chunks.embedding`` was created in migration 013 as a fixed
``vector(1536)``. Profile A (BGE-M3, 1024 dim) cannot be stored in that column
because pgvector enforces the dim constraint on INSERT.

Solution (Strategy B, requires pgvector ≥ 0.7 — verified 0.8.1 in dev):
- Widen ``rag_chunks.embedding`` from ``vector(1536)`` to flex-dim ``vector``
  so rows of any dimensionality can coexist.
- Add ``rag_collections.embedding_dim`` (INT, NOT NULL, default 1536) so the
  retrieval layer knows which vector size to produce for each collection.
- Backfill existing rows: collections stay at 1536, chunks already have
  their ``embedding_dim`` populated by alembic 041 or remain NULL.

The previous migration (041) added ``rag_chunks.embedding_dim`` as the
per-row dim marker. Together, they allow the retrieval layer to:
  1. Look up ``rag_collections.embedding_dim`` to pick the right embedder.
  2. Scope search queries with ``WHERE embedding_dim = :dim`` so pgvector
     never compares vectors across dimensionalities.

Zero-downtime: the type widening is an in-place catalog change, no rewrite.
The new ``embedding_dim`` column on collections defaults to 1536 so existing
API calls stay functional.

No HNSW index exists on rag_chunks today — seq-scan is the current baseline
and stays unchanged. Production can add per-dim partial indices
(``CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WHERE embedding_dim = N``)
when query volume warrants it.

Downgrade: narrow ``rag_chunks.embedding`` back to ``vector(1536)`` — this
WILL fail if any row holds a non-1536 vector. Drop the collections column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "042"
down_revision: str | None = "041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE vector")

    op.add_column(
        "rag_collections",
        sa.Column(
            "embedding_dim",
            sa.Integer(),
            nullable=False,
            server_default="1536",
        ),
    )


def downgrade() -> None:
    op.drop_column("rag_collections", "embedding_dim")
    op.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE vector(1536)")
