"""Add document_type_configs table for configurable document extraction.

Revision ID: 015
Revises: 014
Create Date: 2026-04-01

Adds:
- document_type_configs: configurable extraction schemas per document type
  (e.g., invoice, contract, receipt). Each config defines fields to extract,
  validation rules, parser preference, and LLM model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_type_configs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        # Parser configuration
        sa.Column(
            "parser",
            sa.String(50),
            nullable=False,
            server_default="docling",
        ),
        sa.Column("extraction_model", sa.String(100), server_default="openai/gpt-4o"),
        # Field definitions as JSONB array
        # Each field: {name, type, description, required, default}
        sa.Column("fields", JSONB, nullable=False, server_default="[]"),
        # Validation rules as JSONB array
        # Each rule: string expression or {rule, message}
        sa.Column("validation_rules", JSONB, server_default="[]"),
        # Output format options
        sa.Column(
            "output_formats",
            JSONB,
            server_default='["json"]',
        ),
        # Multi-tenant
        sa.Column("customer", sa.String(100), server_default="default"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("version", sa.Integer, server_default="1"),
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
    )
    op.create_index(
        "idx_doc_type_configs_customer",
        "document_type_configs",
        ["customer"],
    )
    op.create_index(
        "idx_doc_type_configs_type",
        "document_type_configs",
        ["document_type"],
    )

    # Seed default invoice config
    op.execute("""
        INSERT INTO document_type_configs (name, display_name, document_type, description, parser, extraction_model, fields, validation_rules, output_formats, customer)
        VALUES (
            'invoice-hu',
            'Hungarian Invoice',
            'invoice',
            'Standard Hungarian invoice extraction (szamla)',
            'docling',
            'openai/gpt-4o',
            '[
                {"name": "vendor_name", "type": "string", "description": "Szallito neve", "required": true},
                {"name": "vendor_address", "type": "string", "description": "Szallito cime", "required": false},
                {"name": "vendor_tax_number", "type": "string", "description": "Szallito adoszama", "required": false},
                {"name": "buyer_name", "type": "string", "description": "Vevo neve", "required": true},
                {"name": "buyer_address", "type": "string", "description": "Vevo cime", "required": false},
                {"name": "buyer_tax_number", "type": "string", "description": "Vevo adoszama", "required": false},
                {"name": "invoice_number", "type": "string", "description": "Szamlaszam", "required": true},
                {"name": "invoice_date", "type": "date", "description": "Szamla kelte", "required": true},
                {"name": "fulfillment_date", "type": "date", "description": "Teljesites datuma", "required": false},
                {"name": "due_date", "type": "date", "description": "Fizetesi hatarido", "required": false},
                {"name": "currency", "type": "string", "description": "Penznem", "required": false, "default": "HUF"},
                {"name": "net_total", "type": "number", "description": "Netto osszeg", "required": true},
                {"name": "vat_total", "type": "number", "description": "AFA osszeg", "required": true},
                {"name": "gross_total", "type": "number", "description": "Brutto osszeg", "required": true},
                {"name": "line_items", "type": "list[object]", "description": "Szamla tetelek", "required": false}
            ]'::jsonb,
            '["net_total + vat_total == gross_total"]'::jsonb,
            '["json", "csv", "excel"]'::jsonb,
            'default'
        )
    """)


def downgrade() -> None:
    op.drop_table("document_type_configs")
