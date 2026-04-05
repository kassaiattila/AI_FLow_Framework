"""Add outlook_com to email_connector_configs provider constraint.

Revision ID: 026
Revises: 025
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers
revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("chk_ecc_provider", "email_connector_configs", type_="check")
    op.create_check_constraint(
        "chk_ecc_provider",
        "email_connector_configs",
        "provider IN ('imap', 'o365_graph', 'gmail', 'outlook_com')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_ecc_provider", "email_connector_configs", type_="check")
    op.create_check_constraint(
        "chk_ecc_provider",
        "email_connector_configs",
        "provider IN ('imap', 'o365_graph', 'gmail')",
    )
