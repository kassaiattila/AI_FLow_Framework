"""Harden intake_packages.source_type — backfill + CHECK constraint.

Revision ID: 034
Revises: 033
Create Date: 2026-04-22

Phase 1b Week 1 Day 1 (E0.2):
- Backfill any stray NULL source_type rows with 'legacy' (defensive; 032 already set NOT NULL).
- Re-assert NOT NULL (idempotent safety).
- Add CHECK constraint enumerating every source_type Phase 1b + legacy supports.

Allowed values tracked in aiflow.intake.package.IntakeSourceType plus 'legacy'
sentinel for pre-Phase-1a rows migrated from older schemas.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "034"
down_revision: str | None = "033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SOURCE_TYPE_VALUES = (
    "email",
    "file_upload",
    "folder_import",
    "batch_import",
    "api_push",
    "legacy",
)


def upgrade() -> None:
    op.execute("UPDATE intake_packages SET source_type = 'legacy' WHERE source_type IS NULL")
    op.alter_column("intake_packages", "source_type", nullable=False)

    values_sql = ", ".join(f"'{v}'" for v in _SOURCE_TYPE_VALUES)
    op.create_check_constraint(
        "ck_intake_source_type",
        "intake_packages",
        f"source_type IN ({values_sql})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_intake_source_type", "intake_packages", type_="check")
    op.alter_column("intake_packages", "source_type", nullable=True)
