"""Add model registry and embedding models tables.

Revision ID: 003
Revises: 002
Create Date: 2026-03-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "model_registry",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("lifecycle", sa.String(50), server_default="registered"),
        sa.Column("serving_mode", sa.String(50), nullable=False),
        sa.Column("endpoint_url", sa.Text),
        sa.Column("model_path", sa.Text),
        sa.Column("capabilities", JSONB, server_default="[]"),
        sa.Column("pricing_model", sa.String(50), server_default="per_token"),
        sa.Column("cost_per_input_token", sa.Numeric(12, 8), server_default="0"),
        sa.Column("cost_per_output_token", sa.Numeric(12, 8), server_default="0"),
        sa.Column("cost_per_request", sa.Numeric(10, 6), server_default="0"),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("fallback_model", sa.String(255)),
        sa.Column("avg_latency_ms", sa.Float),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_mr_model_type", "model_registry", ["model_type"])
    op.create_index("idx_mr_lifecycle", "model_registry", ["lifecycle"])
    op.create_index("idx_mr_provider", "model_registry", ["provider"])

    op.create_table(
        "embedding_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_id", UUID(as_uuid=True), sa.ForeignKey("model_registry.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("dimensions", sa.Integer, nullable=False),
        sa.Column("max_input_tokens", sa.Integer, nullable=False, server_default="8192"),
        sa.Column("supports_batch", sa.Boolean, server_default="true"),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_em_model_id", "embedding_models", ["model_id"])

def downgrade() -> None:
    op.drop_table("embedding_models")
    op.drop_table("model_registry")
