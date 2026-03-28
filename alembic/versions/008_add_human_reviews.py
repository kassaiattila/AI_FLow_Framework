"""Add human reviews table.

Revision ID: 008
Revises: 007
Create Date: 2026-03-28

Adds:
- human_reviews: human-in-the-loop review requests and decisions
- Indexes: status, workflow_run_id, reviewer_id
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- human_reviews table ---
    op.create_table(
        "human_reviews",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workflow_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("context", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("options", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("priority", sa.Integer, server_default="0", nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("decision", sa.Text),
        sa.Column("feedback", sa.Text),
        sa.Column(
            "reviewer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    # --- indexes ---
    op.create_index(
        "idx_human_reviews_status",
        "human_reviews",
        ["status"],
    )
    op.create_index(
        "idx_human_reviews_workflow_run_id",
        "human_reviews",
        ["workflow_run_id"],
    )
    op.create_index(
        "idx_human_reviews_reviewer_id",
        "human_reviews",
        ["reviewer_id"],
    )


def downgrade() -> None:
    op.drop_table("human_reviews")
