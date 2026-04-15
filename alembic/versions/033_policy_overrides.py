"""Add policy_overrides table for tenant-specific policy configuration.

Revision ID: 033
Revises: 032
Create Date: 2026-04-15

Adds:
- policy_overrides: tenant/instance-level PolicyConfig overrides stored as JSONB
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "033"
down_revision: str | None = "032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_overrides",
        sa.Column(
            "override_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("instance_id", sa.String(255), nullable=True),
        sa.Column(
            "policy_json",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_policy_overrides_tenant", "policy_overrides", ["tenant_id"])
    op.create_unique_constraint(
        "uq_policy_overrides_tenant_instance",
        "policy_overrides",
        ["tenant_id", "instance_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_policy_overrides_tenant_instance", "policy_overrides")
    op.drop_index("idx_policy_overrides_tenant")
    op.drop_table("policy_overrides")
