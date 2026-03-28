"""Add monitoring aggregate views.

Revision ID: 011
Revises: 010
Create Date: 2026-03-28

Adds:
- v_workflow_metrics: daily workflow run statistics and SLA tracking
- v_model_usage: daily model call counts, tokens, and costs
- v_test_trends: daily test pass rates and execution costs per dataset/skill
"""

from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- v_workflow_metrics view ---
    op.execute(
        """
        CREATE OR REPLACE VIEW v_workflow_metrics AS
        SELECT
            wr.workflow_name,
            DATE(wr.started_at)                         AS day,
            COUNT(*)                                    AS total_runs,
            COUNT(*) FILTER (WHERE wr.status = 'completed')
                                                        AS successful,
            COUNT(*) FILTER (WHERE wr.status = 'failed')
                                                        AS failed,
            CASE
                WHEN COUNT(*) > 0
                THEN ROUND(
                    COUNT(*) FILTER (WHERE wr.status = 'completed')::numeric
                    / COUNT(*)::numeric * 100, 2
                )
                ELSE 0
            END                                         AS success_rate,
            ROUND(
                AVG(
                    EXTRACT(EPOCH FROM (wr.finished_at - wr.started_at))
                )::numeric, 3
            )                                           AS avg_duration_s,
            ROUND(
                PERCENTILE_CONT(0.95) WITHIN GROUP (
                    ORDER BY EXTRACT(EPOCH FROM (wr.finished_at - wr.started_at))
                )::numeric, 3
            )                                           AS p95_duration_s,
            COALESCE(SUM(cr.cost_usd), 0)              AS total_cost_usd,
            CASE
                WHEN COUNT(*) > 0
                THEN ROUND(
                    COUNT(*) FILTER (
                        WHERE wr.status = 'completed'
                          AND EXTRACT(EPOCH FROM (wr.finished_at - wr.started_at)) <= 30
                    )::numeric
                    / COUNT(*)::numeric * 100, 2
                )
                ELSE 0
            END                                         AS sla_pct
        FROM workflow_runs wr
        LEFT JOIN LATERAL (
            SELECT SUM(c.cost_usd) AS cost_usd
            FROM cost_records c
            WHERE c.workflow_run_id = wr.id
        ) cr ON TRUE
        GROUP BY wr.workflow_name, DATE(wr.started_at)
        ORDER BY day DESC, total_runs DESC;
        """
    )

    # --- v_model_usage view ---
    op.execute(
        """
        CREATE OR REPLACE VIEW v_model_usage AS
        SELECT
            cr.model,
            DATE(cr.recorded_at)                        AS day,
            COUNT(*)                                    AS call_count,
            SUM(cr.input_tokens + cr.output_tokens)     AS total_tokens,
            SUM(cr.cost_usd)                           AS total_cost_usd
        FROM cost_records cr
        GROUP BY cr.model, DATE(cr.recorded_at)
        ORDER BY day DESC, total_cost_usd DESC;
        """
    )

    # --- v_test_trends view ---
    op.execute(
        """
        CREATE OR REPLACE VIEW v_test_trends AS
        SELECT
            td.name                                     AS dataset,
            td.skill_name                               AS skill,
            DATE(tr.executed_at)                        AS day,
            COUNT(*)                                    AS total_tests,
            COUNT(*) FILTER (WHERE tr.passed = true)    AS passed,
            CASE
                WHEN COUNT(*) > 0
                THEN ROUND(
                    COUNT(*) FILTER (WHERE tr.passed = true)::numeric
                    / COUNT(*)::numeric * 100, 2
                )
                ELSE 0
            END                                         AS pass_rate,
            ROUND(AVG(tr.duration_ms)::numeric, 2)      AS avg_duration_ms,
            COALESCE(SUM(tr.cost_usd), 0)              AS total_cost_usd
        FROM test_results tr
        JOIN test_cases tc ON tc.id = tr.test_case_id
        JOIN test_datasets td ON td.id = tc.dataset_id
        GROUP BY td.name, td.skill_name, DATE(tr.executed_at)
        ORDER BY day DESC, dataset;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_test_trends;")
    op.execute("DROP VIEW IF EXISTS v_model_usage;")
    op.execute("DROP VIEW IF EXISTS v_workflow_metrics;")
