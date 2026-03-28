"""Add test management tables.

Revision ID: 010
Revises: 009
Create Date: 2026-03-28

Adds:
- test_datasets: named test collections per skill
- test_cases: individual test inputs and expected outputs
- test_results: execution results with scores and costs
- Indexes: dataset_id, run_id, executed_at
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- test_datasets table ---
    op.create_table(
        "test_datasets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("test_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tags", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- test_cases table ---
    op.create_table(
        "test_cases",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "dataset_id",
            UUID(as_uuid=True),
            sa.ForeignKey("test_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("input_data", JSONB, nullable=False),
        sa.Column("expected_output", JSONB),
        sa.Column("assertions", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tags", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("priority", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- test_results table ---
    op.create_table(
        "test_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "test_case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(255), nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("actual_output", JSONB),
        sa.Column("scores", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.Text),
        sa.Column("duration_ms", sa.Float),
        sa.Column("cost_usd", sa.Numeric(12, 6)),
        sa.Column("model_used", sa.String(255)),
        sa.Column("prompt_version", sa.String(100)),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- indexes ---
    op.create_index(
        "idx_test_cases_dataset_id",
        "test_cases",
        ["dataset_id"],
    )
    op.create_index(
        "idx_test_results_run_id",
        "test_results",
        ["run_id"],
    )
    op.create_index(
        "idx_test_results_executed_at",
        "test_results",
        [sa.text("executed_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("test_results")
    op.drop_table("test_cases")
    op.drop_table("test_datasets")
