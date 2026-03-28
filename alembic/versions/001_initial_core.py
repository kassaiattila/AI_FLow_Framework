"""Initial core tables: workflow_runs, step_runs.

Revision ID: 001
Revises: None
Create Date: 2026-03-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_name", sa.String(255), nullable=False),
        sa.Column("workflow_version", sa.String(50), nullable=False),
        sa.Column("skill_name", sa.String(255)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_data", JSONB, nullable=False),
        sa.Column("output_data", JSONB),
        sa.Column("error", sa.Text),
        sa.Column("error_type", sa.String(100)),
        sa.Column("trace_id", sa.String(255)),
        sa.Column("trace_url", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("total_duration_ms", sa.Float),
        sa.Column("total_cost_usd", sa.Float, server_default="0"),
        sa.Column("sla_target_seconds", sa.Integer),
        sa.Column("sla_met", sa.Boolean),
        sa.Column("team_id", UUID(as_uuid=True)),  # FK added in migration 005
        sa.Column("user_id", UUID(as_uuid=True)),  # FK added in migration 005
        sa.Column("job_id", sa.String(255)),
        sa.Column("priority", sa.Integer, server_default="3"),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'paused', 'cancelled')",
            name="chk_workflow_runs_status",
        ),
    )
    op.create_index("idx_wr_workflow_name", "workflow_runs", ["workflow_name"])
    op.create_index("idx_wr_status", "workflow_runs", ["status"])
    op.create_index("idx_wr_team_id", "workflow_runs", ["team_id"])
    op.create_index("idx_wr_user_id", "workflow_runs", ["user_id"])
    op.create_index("idx_wr_skill_name", "workflow_runs", ["skill_name"])
    op.create_index("idx_wr_created_at", "workflow_runs", ["created_at"])
    op.create_index("idx_wr_job_id", "workflow_runs", ["job_id"])

    op.create_table(
        "step_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_run_id", UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_data", JSONB),
        sa.Column("output_data", JSONB),
        sa.Column("error", sa.Text),
        sa.Column("error_type", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Float),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("max_retries", sa.Integer, server_default="3"),
        sa.Column("cost_usd", sa.Float, server_default="0"),
        sa.Column("model_used", sa.String(100)),
        sa.Column("input_tokens", sa.Integer),
        sa.Column("output_tokens", sa.Integer),
        sa.Column("scores", JSONB, server_default="{}"),
        sa.Column("quality_gate_passed", sa.Boolean),
        sa.Column("checkpoint_data", JSONB),
        sa.Column("checkpoint_version", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_sr_workflow_run_id", "step_runs", ["workflow_run_id"])
    op.create_index("idx_sr_step_name", "step_runs", ["step_name"])
    op.create_index("idx_sr_status", "step_runs", ["status"])


def downgrade() -> None:
    op.drop_table("step_runs")
    op.drop_table("workflow_runs")
