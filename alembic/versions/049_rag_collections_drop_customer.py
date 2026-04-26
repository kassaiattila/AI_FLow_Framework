"""Drop ``rag_collections.customer`` — multi-tenant cleanup.

Revision ID: 049
Revises: 048
Create Date: 2026-04-26

Sprint W / SW-3 — closes SS-FU-1 / SS-FU-5.

Sprint S S143 (migration 046) introduced ``rag_collections.tenant_id`` with a
``'default'`` server default; S144 wired the per-tenant admin UI; S145 swapped
the legacy ``UNIQUE (name)`` constraint for ``UNIQUE (tenant_id, name)``. At
that point ``customer`` lost every consumer that wasn't a defensive default.

The Sprint S retro flagged the column drop as SS-FU-1 / SS-FU-5 and explicitly
deferred it to a later sprint so the rename could land alongside the service
code refactor. Sprint W SW-3 finishes the job:

* Pre-flight (operator-driven, **NOT** in the migration body): run
  ``SELECT COUNT(*) FROM rag_collections WHERE customer IS NOT NULL
   AND customer != tenant_id``. Non-zero → halt + manual review.
  Dev / staging snapshot at SW-3 prep returned 0.
* Upgrade drops the column; the table loses ~2-byte tracking overhead per row.
* Downgrade restores the column as nullable text — the prior NOT NULL with
  ``customer = 'default'`` server default cannot be auto-restored without
  rewriting rows, and SS-FU-5 already authorized the lossy path.

Idempotent + reversible (within the lossy boundary above).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "049"
down_revision: str | None = "048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("idx_rag_collections_customer", table_name="rag_collections")
    op.drop_column("rag_collections", "customer")


def downgrade() -> None:
    op.add_column(
        "rag_collections",
        sa.Column("customer", sa.String(100), nullable=True),
    )
    op.create_index(
        "idx_rag_collections_customer",
        "rag_collections",
        ["customer"],
    )
