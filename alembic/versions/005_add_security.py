"""Add security tables: teams, users, audit_log + workflow_runs FK.

Revision ID: 005
Revises: 004
Create Date: 2026-03-28

Adds:
- teams: multi-tenant team management with monthly budgets
- users: user accounts with API key auth and team membership
- audit_log: comprehensive audit trail for all actions
- ALTER workflow_runs: add FK team_id -> teams, user_id -> users
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- teams table ---
    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("budget_monthly_usd", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("budget_used_usd", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("budget_reset_day", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- users table ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL")),
        sa.Column("role", sa.String(50), server_default="viewer", nullable=False),
        sa.Column("api_key_hash", sa.String(64)),
        sa.Column("api_key_prefix", sa.String(8)),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_users_team_id", "users", ["team_id"])
    op.create_index("idx_users_api_key_prefix", "users", ["api_key_prefix"])

    # --- audit_log table ---
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255)),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("duration_ms", sa.Integer),
    )
    op.create_index("idx_audit_log_timestamp", "audit_log", [sa.text("timestamp DESC")])
    op.create_index("idx_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("idx_audit_log_team_id", "audit_log", ["team_id"])
    op.create_index("idx_audit_log_action", "audit_log", ["action"])
    op.create_index("idx_audit_log_resource", "audit_log", ["resource_type", "resource_id"])

    # --- ALTER workflow_runs: add FK columns ---
    op.add_column("workflow_runs", sa.Column("team_id", UUID(as_uuid=True)))
    op.add_column("workflow_runs", sa.Column("user_id", UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_workflow_runs_team_id",
        "workflow_runs",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_workflow_runs_user_id",
        "workflow_runs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Remove FK columns from workflow_runs
    op.drop_constraint("fk_workflow_runs_user_id", "workflow_runs", type_="foreignkey")
    op.drop_constraint("fk_workflow_runs_team_id", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "user_id")
    op.drop_column("workflow_runs", "team_id")

    # Drop tables in reverse dependency order
    op.drop_table("audit_log")
    op.drop_table("users")
    op.drop_table("teams")
