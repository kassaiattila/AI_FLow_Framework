"""Add ``tenant_budgets`` — per-tenant spending limits keyed on (tenant_id, period).

Revision ID: 045
Revises: 044
Create Date: 2026-04-27

Sprint N / S121 — pre-flight cost guardrail groundwork.

Sibling to ``teams.budget_monthly_usd`` (Alembic 006) / ``v_monthly_budget``:
tenants and teams are distinct v2 boundaries (tenant_id is the string
multi-tenancy key; team_id is a UUID grouping inside a tenant). Keeping the
teams-era view in place preserves existing dashboards; ``tenant_budgets``
drives the new pre-flight guardrail shipped in S122.

Additive — creates a fresh table + unique index + single-column lookup
index. No existing column is touched, so upgrade is zero-downtime and
downgrade is a plain ``DROP TABLE``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "045"
down_revision: str | None = "044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenant_budgets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("limit_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column(
            "alert_threshold_pct",
            ARRAY(sa.Integer),
            nullable=False,
            server_default=sa.text("'{50,80,95}'::integer[]"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "period IN ('daily','monthly')",
            name="ck_tenant_budgets_period",
        ),
        sa.CheckConstraint(
            "limit_usd >= 0",
            name="ck_tenant_budgets_limit_nonneg",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "period",
            name="uq_tenant_budgets_tenant_period",
        ),
    )
    op.create_index(
        "idx_tenant_budgets_tenant_id",
        "tenant_budgets",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_tenant_budgets_tenant_id", table_name="tenant_budgets")
    op.drop_table("tenant_budgets")
