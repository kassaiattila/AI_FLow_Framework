"""Add password_hash column to users table for bcrypt authentication.

Revision ID: 025
Revises: 024
Create Date: 2026-04-02

Changes:
- ALTER users ADD COLUMN password_hash VARCHAR(128) — stores bcrypt hash
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
