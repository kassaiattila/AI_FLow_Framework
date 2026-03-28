"""Add A/B testing tables.

Revision ID: 009
Revises: 008
Create Date: 2026-03-28

Adds:
- ab_experiments: experiment definitions with variants and traffic splits
- ab_assignments: user-to-variant assignments
- ab_outcomes: recorded metrics per assignment
- Indexes: experiment_id for assignments and outcomes
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ab_experiments table ---
    op.create_table(
        "ab_experiments",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("prompt_name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("variants", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("traffic_split", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )

    # --- ab_assignments table ---
    op.create_table(
        "ab_assignments",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "experiment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ab_experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("variant", sa.String(100), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- ab_outcomes table ---
    op.create_table(
        "ab_outcomes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "experiment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ab_experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ab_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("variant", sa.String(100), nullable=False),
        sa.Column("metrics", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- indexes ---
    op.create_index(
        "idx_ab_assignments_experiment_id",
        "ab_assignments",
        ["experiment_id"],
    )
    op.create_index(
        "idx_ab_outcomes_experiment_id",
        "ab_outcomes",
        ["experiment_id"],
    )


def downgrade() -> None:
    op.drop_table("ab_outcomes")
    op.drop_table("ab_assignments")
    op.drop_table("ab_experiments")
