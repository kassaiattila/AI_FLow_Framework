"""Add service_config_versions table for config versioning.

Revision ID: 014
Revises: 013
Create Date: 2026-04-01

Adds:
- service_config_versions: versioned config snapshots per service instance
  with deploy/rollback support and audit trail
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_config_versions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "service_instance_id",
            UUID(as_uuid=True),
            sa.ForeignKey("skill_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("config_jsonb", JSONB, nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True)),
        sa.Column("deployed_by", sa.String(100)),
        sa.Column("is_active", sa.Boolean, server_default="false"),
        sa.Column("change_description", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "service_instance_id", "version", name="uq_config_version"
        ),
    )
    # Index for fast active config lookup
    op.create_index(
        "idx_config_versions_active",
        "service_config_versions",
        ["service_instance_id", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )
    # Index for version ordering
    op.create_index(
        "idx_config_versions_instance_version",
        "service_config_versions",
        ["service_instance_id", sa.text("version DESC")],
    )


def downgrade() -> None:
    op.drop_table("service_config_versions")
