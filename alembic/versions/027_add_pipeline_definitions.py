"""Add pipeline_definitions table and workflow_runs.pipeline_id FK.

Revision ID: 027
Revises: 026
Create Date: 2026-04-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create pipeline_definitions table
    op.create_table(
        "pipeline_definitions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "version", sa.String(50), nullable=False, server_default="1.0.0"
        ),
        sa.Column("description", sa.Text),
        sa.Column("yaml_source", sa.Text, nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("trigger_config", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("input_schema", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("team_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("name", "version", name="uq_pd_name_version"),
    )

    op.create_index("idx_pd_name", "pipeline_definitions", ["name"])
    op.create_index("idx_pd_enabled", "pipeline_definitions", ["enabled"])
    op.create_index("idx_pd_team_id", "pipeline_definitions", ["team_id"])

    # 2. Add pipeline_id FK to workflow_runs (nullable, ON DELETE SET NULL)
    op.add_column(
        "workflow_runs",
        sa.Column("pipeline_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_wr_pipeline_id",
        "workflow_runs",
        "pipeline_definitions",
        ["pipeline_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_wr_pipeline_id", "workflow_runs", ["pipeline_id"])


def downgrade() -> None:
    op.drop_index("idx_wr_pipeline_id", table_name="workflow_runs")
    op.drop_constraint(
        "fk_wr_pipeline_id", "workflow_runs", type_="foreignkey"
    )
    op.drop_column("workflow_runs", "pipeline_id")

    op.drop_index("idx_pd_team_id", table_name="pipeline_definitions")
    op.drop_index("idx_pd_enabled", table_name="pipeline_definitions")
    op.drop_index("idx_pd_name", table_name="pipeline_definitions")
    op.drop_table("pipeline_definitions")
