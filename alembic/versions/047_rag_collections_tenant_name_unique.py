"""Replace ``rag_collections.name`` unique with ``(tenant_id, name)`` unique.

Revision ID: 047
Revises: 046
Create Date: 2026-04-26

Sprint S / S145 — operability close-out (SS-FU-4).

Problem: migration 013 created ``rag_collections_name_key`` (UNIQUE on
``name``) when the table was single-tenant. Sprint S S143/S144 introduced
``tenant_id`` (default ``'default'``) and the admin UI for per-tenant
collection management, but the legacy ``UNIQUE (name)`` still blocks two
tenants from picking the same collection name — a hole in the multi-tenant
story flagged in the S143 PR as SS-FU-4.

Solution: drop the name-only unique and replace it with a composite
``UNIQUE (tenant_id, name)``. Two collections may now share a name iff
they belong to different tenants; uniqueness within a tenant is
preserved.

Pre-flight: dev DB scan ``SELECT tenant_id, name, COUNT(*) FROM
rag_collections GROUP BY tenant_id, name HAVING COUNT(*) > 1`` returned
zero rows, confirming the swap is safe with current production-shaped
data. Operators with duplicates must dedup before running this
migration.

Idempotent + reversible:
- Upgrade drops the old constraint then adds the composite one.
- Downgrade reverses (drops composite, restores name-only).
- Both directions take a brief metadata-only lock (no row rewrites).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "047"
down_revision: str | None = "046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "rag_collections_name_key",
        "rag_collections",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_rag_collections_tenant_name",
        "rag_collections",
        ["tenant_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_rag_collections_tenant_name",
        "rag_collections",
        type_="unique",
    )
    op.create_unique_constraint(
        "rag_collections_name_key",
        "rag_collections",
        ["name"],
    )
