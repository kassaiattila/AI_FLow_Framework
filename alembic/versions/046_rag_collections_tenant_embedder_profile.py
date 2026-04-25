"""Add ``rag_collections.tenant_id`` + ``rag_collections.embedder_profile_id``.

Revision ID: 046
Revises: 045
Create Date: 2026-05-15

Sprint S / S143 — functional vector DB teljes kör.

Problem: ``RagEngineService.query()`` hardcodes ``self._embedder`` on the
constructor, so 1024-dim BGE-M3 Profile A collections ingested via the
ProviderRegistry (Sprint J S100) cannot be queried — the query path always
produces a single dim's worth of query-vector regardless of what the
collection actually stores. The Sprint J retro listed this as the oldest
open carry-forward (FU-1).

Solution: let each ``rag_collections`` row pin which ProviderRegistry
embedder profile to use at query time. Sprint S S143 adds the column +
updates ``RagEngineService.query()`` to resolve the embedder through the
registry when a profile is set, with NULL fallback to the existing
constructor embedder (backward-compat for every currently-live 1536-dim
collection).

The ``tenant_id`` column lands in the same migration to give S144 (admin
UI per-tenant collection list) a ready multi-tenancy key. It defaults to
``'default'`` so every pre-existing row gets a valid tenant scope with
zero operator action.

Additive + zero-downtime:
- Two nullable-equivalent columns (``tenant_id`` has a server default, so
  INSERTs that don't name it still succeed — no code break).
- One single-column lookup index on ``tenant_id``.
- No unique constraint on ``(tenant_id, name)`` yet — S144 will add that
  once the admin UI can upsert real tenants. Today every row has tenant_id
  = 'default' and the pre-existing name uniqueness (migration 013) still
  holds.
- Downgrade drops the index + both columns in reverse order.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "046"
down_revision: str | None = "045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rag_collections",
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
    )
    op.add_column(
        "rag_collections",
        sa.Column(
            "embedder_profile_id",
            sa.Text(),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_rag_collections_tenant_id",
        "rag_collections",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rag_collections_tenant_id", table_name="rag_collections")
    op.drop_column("rag_collections", "embedder_profile_id")
    op.drop_column("rag_collections", "tenant_id")
