"""Add skill_instances table and workflow_runs.instance_id FK.

Revision ID: 012
Revises: 011
Create Date: 2026-03-28

Adds:
- skill_instances: configured deployments of skill templates per customer
- workflow_runs.instance_id: FK linking runs to their instance
- v_instance_stats: aggregate view for per-instance metrics
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. skill_instances table
    op.create_table(
        "skill_instances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("instance_name", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("customer", sa.String(100), nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_version", sa.String(50), nullable=False),
        sa.Column("config", JSONB, nullable=False),
        sa.Column("prompt_namespace", sa.String(255), nullable=False),
        sa.Column("prompt_label", sa.String(50), server_default="prod"),
        sa.Column("default_model", sa.String(100), nullable=False),
        sa.Column("fallback_model", sa.String(100)),
        sa.Column("budget_monthly_usd", sa.Numeric(10, 2)),
        sa.Column("budget_used_usd", sa.Numeric(10, 2), server_default="0"),
        sa.Column("budget_per_run_usd", sa.Numeric(10, 4)),
        sa.Column("budget_reset_day", sa.Integer, server_default="1"),
        sa.Column("sla_target_seconds", sa.Integer),
        sa.Column("sla_p95_target_seconds", sa.Integer),
        sa.Column("input_channel", sa.String(50), server_default="api"),
        sa.Column("output_channel", sa.String(50), server_default="api"),
        sa.Column("queue_name", sa.String(255)),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("total_runs", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", sa.String(255)),
        sa.Column("updated_by", sa.String(255)),
        sa.ForeignKeyConstraint(["skill_name"], ["skills.name"]),
        sa.CheckConstraint(
            "status IN ('active','paused','deprecated','error')",
            name="chk_si_status",
        ),
        sa.CheckConstraint(
            "input_channel IN ('api','email','webhook','queue')",
            name="chk_si_input",
        ),
        sa.CheckConstraint(
            "output_channel IN ('api','email','webhook','db')",
            name="chk_si_output",
        ),
    )

    # 2. Indexes
    op.create_index("idx_si_customer", "skill_instances", ["customer"])
    op.create_index("idx_si_skill_name", "skill_instances", ["skill_name"])
    op.create_index("idx_si_enabled", "skill_instances", ["enabled"],
                    postgresql_where=sa.text("enabled = TRUE"))
    op.create_index("idx_si_status", "skill_instances", ["status"])
    op.create_index("idx_si_customer_skill", "skill_instances", ["customer", "skill_name"])
    op.create_index("idx_si_prompt_namespace", "skill_instances", ["prompt_namespace"])
    op.create_index("idx_si_config_gin", "skill_instances", ["config"],
                    postgresql_using="gin",
                    postgresql_ops={"config": "jsonb_path_ops"})

    # 3. workflow_runs.instance_id FK
    op.add_column("workflow_runs",
                  sa.Column("instance_id", UUID(as_uuid=True)))
    op.create_foreign_key("fk_wr_instance_id", "workflow_runs", "skill_instances",
                          ["instance_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_wr_instance_id", "workflow_runs", ["instance_id"])

    # 4. v_instance_stats aggregate view
    op.execute("""
        CREATE OR REPLACE VIEW v_instance_stats AS
        SELECT
            si.id AS instance_id,
            si.instance_name,
            si.customer,
            si.skill_name,
            si.display_name,
            si.enabled,
            si.status,
            COUNT(wr.id) AS total_runs,
            COUNT(wr.id) FILTER (WHERE wr.status = 'completed') AS completed_runs,
            COUNT(wr.id) FILTER (WHERE wr.status = 'failed') AS failed_runs,
            AVG(wr.total_duration_ms) FILTER (WHERE wr.status = 'completed') AS avg_duration_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY wr.total_duration_ms)
                FILTER (WHERE wr.status = 'completed') AS p95_duration_ms,
            SUM(wr.total_cost_usd) AS total_cost_usd,
            MAX(wr.created_at) AS last_run_at,
            AVG(CASE WHEN wr.sla_met THEN 1.0 ELSE 0.0 END) AS sla_met_ratio
        FROM skill_instances si
        LEFT JOIN workflow_runs wr ON wr.instance_id = si.id
        GROUP BY si.id, si.instance_name, si.customer, si.skill_name,
                 si.display_name, si.enabled, si.status
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_instance_stats")
    op.drop_index("idx_wr_instance_id", "workflow_runs")
    op.drop_constraint("fk_wr_instance_id", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "instance_id")
    op.drop_table("skill_instances")
