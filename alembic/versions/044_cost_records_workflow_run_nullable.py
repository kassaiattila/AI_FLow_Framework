"""Relax cost_records.workflow_run_id to NULL-able.

Revision ID: 044
Revises: 043
Create Date: 2026-04-24

Sprint L / S112 follow-up — tenant-level cost cap aggregation
(``PolicyEngine.enforce_cost_cap``) emits ``CostAttribution`` rows that are
not always tied to a specific ``workflow_run``. The original constraint
(``NOT NULL`` from migration 006, tied to ``workflow_runs.id`` via FK) made
sense for per-run cost dashboards but blocks the new tenant-scoped path —
integration tests for S112 fail with ``NotNullViolationError`` because the
repository converts an empty ``run_id`` to ``NULL``.

Loosening ``NOT NULL`` is a zero-downtime migration (adding NULL to the
accepted domain never invalidates existing rows or queries). The FK to
``workflow_runs(id)`` is preserved — cost rows that reference a run still
cascade-delete cleanly.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "044"
down_revision: str | None = "043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "cost_records",
        "workflow_run_id",
        nullable=True,
    )


def downgrade() -> None:
    # Safe only when no NULL rows exist. Existing tenant-level rows (NULL
    # workflow_run_id) would block this — operator must reconcile first.
    op.alter_column(
        "cost_records",
        "workflow_run_id",
        nullable=False,
    )
