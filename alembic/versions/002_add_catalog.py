"""Add catalog tables: skills, workflow_definitions, skill_prompt_versions.

Revision ID: 002
Revises: 001
Create Date: 2026-03-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("skill_type", sa.String(20), server_default="ai"),
        sa.Column("description", sa.Text),
        sa.Column("author", sa.String(255)),
        sa.Column("manifest", JSONB, nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "workflow_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="SET NULL")),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("complexity", sa.String(20), server_default="medium"),
        sa.Column("dag_definition", JSONB, nullable=False),
        sa.Column("step_definitions", JSONB, nullable=False),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_wd_skill_id", "workflow_definitions", ["skill_id"])

    op.create_table(
        "skill_prompt_versions",
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_version", sa.String(50), nullable=False),
        sa.Column("prompt_name", sa.String(255), nullable=False),
        sa.Column("langfuse_version", sa.Integer, nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("skill_name", "skill_version", "prompt_name"),
    )


def downgrade() -> None:
    op.drop_table("skill_prompt_versions")
    op.drop_table("workflow_definitions")
    op.drop_table("skills")
