"""Add service_metrics table for service call tracking.

Revision ID: 029
Revises: 028
Create Date: 2026-04-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_metrics",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("call_count", sa.Integer, server_default="0"),
        sa.Column("success_count", sa.Integer, server_default="0"),
        sa.Column("error_count", sa.Integer, server_default="0"),
        sa.Column("total_duration_ms", sa.BigInteger, server_default="0"),
        sa.Column("min_duration_ms", sa.Integer, nullable=True),
        sa.Column("max_duration_ms", sa.Integer, nullable=True),
        sa.Column("total_cost", sa.Numeric(12, 6), server_default="0"),
        sa.Column(
            "period",
            sa.String(50),
            nullable=False,
            server_default="hourly",
        ),
        sa.Column(
            "sampled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_sm_service_name", "service_metrics", ["service_name"])
    op.create_index("idx_sm_sampled_at", "service_metrics", ["sampled_at"])
    op.create_index(
        "idx_sm_service_sampled",
        "service_metrics",
        ["service_name", "sampled_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_sm_service_sampled", table_name="service_metrics")
    op.drop_index("idx_sm_sampled_at", table_name="service_metrics")
    op.drop_index("idx_sm_service_name", table_name="service_metrics")
    op.drop_table("service_metrics")
