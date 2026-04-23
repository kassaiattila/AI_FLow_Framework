"""Add tenant_id to cost_records + helper index for cost cap aggregation.

Revision ID: 043
Revises: 042
Create Date: 2026-04-24

Sprint L / S112 — PolicyEngine.cost_cap enforcement needs per-tenant
running-cost aggregation. The existing ``cost_records`` table (Alembic 006)
tracks ``team_id`` but v2 multi-tenancy keys on string ``tenant_id``. This
migration adds a nullable ``tenant_id`` column plus a composite index
``(tenant_id, recorded_at DESC)`` so the cap query stays sub-millisecond
under load. Backfill is left deliberately null — legacy rows remain counted
against ``team_id`` dashboards but not against the new tenant cap.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "043"
down_revision: str | None = "042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cost_records",
        sa.Column("tenant_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "idx_cost_records_tenant_recorded",
        "cost_records",
        ["tenant_id", sa.text("recorded_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_cost_records_tenant_recorded", table_name="cost_records")
    op.drop_column("cost_records", "tenant_id")
