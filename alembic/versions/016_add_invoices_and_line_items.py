"""Add invoices and invoice_line_items tables.

Revision ID: 016
Revises: 015
Create Date: 2026-04-01

Adds:
- invoices: extracted invoice data with vendor/buyer/header/totals
- invoice_line_items: individual line items linked to invoices
Previously these were created with raw SQL in the store_invoice step.
Now managed by Alembic for proper migration support.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Source info
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("source_directory", sa.Text),
        sa.Column("direction", sa.String(20)),
        # Vendor (szallito)
        sa.Column("vendor_name", sa.String(255)),
        sa.Column("vendor_address", sa.Text),
        sa.Column("vendor_tax_number", sa.String(30)),
        sa.Column("vendor_bank_account", sa.String(50)),
        sa.Column("vendor_bank_name", sa.String(255)),
        # Buyer (vevo)
        sa.Column("buyer_name", sa.String(255)),
        sa.Column("buyer_address", sa.Text),
        sa.Column("buyer_tax_number", sa.String(30)),
        # Header
        sa.Column("invoice_number", sa.String(100)),
        sa.Column("invoice_date", sa.Date),
        sa.Column("fulfillment_date", sa.Date),
        sa.Column("due_date", sa.Date),
        sa.Column("currency", sa.String(10), server_default="HUF"),
        sa.Column("payment_method", sa.String(100)),
        sa.Column("invoice_type", sa.String(50), server_default="szamla"),
        # Totals
        sa.Column("net_total", sa.Numeric(14, 2)),
        sa.Column("vat_total", sa.Numeric(14, 2)),
        sa.Column("gross_total", sa.Numeric(14, 2)),
        sa.Column("rounding_amount", sa.Numeric(14, 2)),
        sa.Column("vat_summary", JSONB),
        # Validation
        sa.Column("is_valid", sa.Boolean),
        sa.Column("validation_errors", JSONB),
        sa.Column("confidence_score", sa.Numeric(5, 3)),
        # Extraction metadata
        sa.Column("parser_used", sa.String(50)),
        sa.Column("extraction_model", sa.String(100)),
        sa.Column("raw_text_hash", sa.String(64)),
        sa.Column("extraction_time_ms", sa.Float),
        sa.Column("extraction_cost_usd", sa.Numeric(10, 6)),
        # Document type config reference
        sa.Column("config_name", sa.String(100)),
        # Multi-tenant
        sa.Column("customer", sa.String(100), server_default="default"),
        # Verification
        sa.Column("verified", sa.Boolean, server_default="false"),
        sa.Column("verified_by", sa.String(100)),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("verified_fields", JSONB),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "source_file", "raw_text_hash", name="uq_invoice_source_hash"
        ),
    )
    op.create_index("idx_invoices_customer", "invoices", ["customer"])
    op.create_index("idx_invoices_direction", "invoices", ["direction"])
    op.create_index(
        "idx_invoices_created",
        "invoices",
        [sa.text("created_at DESC")],
    )
    op.create_index("idx_invoices_config", "invoices", ["config_name"])

    op.create_table(
        "invoice_line_items",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer),
        sa.Column("description", sa.Text),
        sa.Column("quantity", sa.Numeric(12, 4)),
        sa.Column("unit", sa.String(20)),
        sa.Column("unit_price", sa.Numeric(14, 2)),
        sa.Column("net_amount", sa.Numeric(14, 2)),
        sa.Column("vat_rate", sa.Numeric(5, 2)),
        sa.Column("vat_amount", sa.Numeric(14, 2)),
        sa.Column("gross_amount", sa.Numeric(14, 2)),
    )
    op.create_index(
        "idx_line_items_invoice",
        "invoice_line_items",
        ["invoice_id"],
    )


def downgrade() -> None:
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
