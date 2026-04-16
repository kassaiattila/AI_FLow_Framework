"""Add intake_packages.association_mode enum column.

Revision ID: 035
Revises: 034
Create Date: 2026-05-02

Phase 1b Week 3 Day 11 (E3.1-A):
- Introduce an ``association_mode`` enum column on ``intake_packages``
  describing how a package's files were matched to its descriptions.
- Zero-downtime: column is nullable (no default); existing rows stay NULL.
  A later migration will backfill + set NOT NULL once N4 is wired into
  every adapter path.

Enum values mirror ``aiflow.intake.associator.AssociationMode``:
    explicit, filename_match, order, single_description
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "035"
down_revision: str | None = "034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ENUM_NAME = "association_mode_enum"
_ENUM_VALUES = ("explicit", "filename_match", "order", "single_description")


def upgrade() -> None:
    association_mode = postgresql.ENUM(
        *_ENUM_VALUES,
        name=_ENUM_NAME,
        create_type=False,
    )
    association_mode.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "intake_packages",
        sa.Column(
            "association_mode",
            association_mode,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("intake_packages", "association_mode")
    association_mode = postgresql.ENUM(
        *_ENUM_VALUES,
        name=_ENUM_NAME,
        create_type=False,
    )
    association_mode.drop(op.get_bind(), checkfirst=True)
