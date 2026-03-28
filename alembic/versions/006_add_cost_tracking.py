"""Add cost tracking tables and budget views.

Revision ID: 006
Revises: 005
Create Date: 2026-03-28

Adds:
- cost_records: per-step LLM cost tracking with token counts
- Indexes: workflow_run_id, team_id, model, recorded_at DESC
- Views: v_daily_team_costs, v_monthly_budget
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- cost_records table ---
    op.create_table(
        "cost_records",
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
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), server_default="0.000000", nullable=False),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- indexes ---
    op.create_index(
        "idx_cost_records_workflow_run_id",
        "cost_records",
        ["workflow_run_id"],
    )
    op.create_index(
        "idx_cost_records_team_id",
        "cost_records",
        ["team_id"],
    )
    op.create_index(
        "idx_cost_records_model",
        "cost_records",
        ["model"],
    )
    op.create_index(
        "idx_cost_records_recorded_at",
        "cost_records",
        [sa.text("recorded_at DESC")],
    )

    # --- views ---
    op.execute(
        """
        CREATE OR REPLACE VIEW v_daily_team_costs AS
        SELECT
            cr.team_id,
            t.name                          AS team_name,
            DATE(cr.recorded_at)            AS cost_date,
            cr.model,
            cr.provider,
            COUNT(*)                        AS request_count,
            SUM(cr.input_tokens)            AS total_input_tokens,
            SUM(cr.output_tokens)           AS total_output_tokens,
            SUM(cr.cost_usd)               AS total_cost_usd
        FROM cost_records cr
        LEFT JOIN teams t ON t.id = cr.team_id
        GROUP BY
            cr.team_id,
            t.name,
            DATE(cr.recorded_at),
            cr.model,
            cr.provider
        ORDER BY cost_date DESC, total_cost_usd DESC;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_monthly_budget AS
        SELECT
            t.id                            AS team_id,
            t.name                          AS team_name,
            t.budget_monthly_usd            AS budget_limit_usd,
            COALESCE(usage.total_cost, 0)   AS used_usd,
            t.budget_monthly_usd
                - COALESCE(usage.total_cost, 0) AS remaining_usd,
            CASE
                WHEN t.budget_monthly_usd > 0
                THEN ROUND(
                    COALESCE(usage.total_cost, 0)
                    / t.budget_monthly_usd * 100, 2
                )
                ELSE 0
            END                             AS usage_pct,
            CASE
                WHEN t.budget_monthly_usd > 0
                    AND COALESCE(usage.total_cost, 0)
                        >= t.budget_monthly_usd         THEN 'exceeded'
                WHEN t.budget_monthly_usd > 0
                    AND COALESCE(usage.total_cost, 0)
                        >= t.budget_monthly_usd * 0.95  THEN 'critical'
                WHEN t.budget_monthly_usd > 0
                    AND COALESCE(usage.total_cost, 0)
                        >= t.budget_monthly_usd * 0.80  THEN 'warning'
                ELSE 'ok'
            END                             AS alert_level
        FROM teams t
        LEFT JOIN LATERAL (
            SELECT SUM(cr.cost_usd) AS total_cost
            FROM cost_records cr
            WHERE cr.team_id = t.id
              AND cr.recorded_at >= DATE_TRUNC('month', NOW())
        ) usage ON TRUE
        ORDER BY usage_pct DESC;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_monthly_budget;")
    op.execute("DROP VIEW IF EXISTS v_daily_team_costs;")
    op.drop_table("cost_records")
