"""Invoice Processor models - I/O types for invoice processing workflow."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

__all__ = [
    "InvoiceParty",
    "InvoiceHeader",
    "LineItem",
    "VatSummaryLine",
    "InvoiceTotals",
    "InvoiceValidation",
    "ProcessedInvoice",
    "InvoiceBatchResult",
]


class InvoiceParty(BaseModel):
    """Vendor (szallito) or buyer (vevo) data."""

    name: str = ""
    address: str = ""
    tax_number: str = ""
    eu_tax_number: str = ""
    bank_account: str = ""
    bank_name: str = ""
    registration_number: str = ""


class InvoiceHeader(BaseModel):
    """Invoice header fields (szamla adatok).

    Sprint U / S156 (SQ-FU-1): the date stamped on the invoice document body
    is exposed primarily as ``issue_date``. ``invoice_date`` is kept as an
    alias for backward compatibility with the SQL column and pre-S156 JSONB
    rows; both names round-trip the same value.
    """

    model_config = ConfigDict(populate_by_name=True)

    invoice_number: str = ""
    issue_date: str = Field(default="", validation_alias=AliasChoices("issue_date", "invoice_date"))
    fulfillment_date: str = ""
    due_date: str = ""
    currency: str = "HUF"
    payment_method: str = ""
    invoice_type: str = "szamla"
    language: str = "hu"

    # Backward-compat read accessor — pre-S156 callers keep using
    # ``header.invoice_date``.
    @property
    def invoice_date(self) -> str:  # type: ignore[override]
        return self.issue_date


class LineItem(BaseModel):
    """Single invoice line item (tetel)."""

    line_number: int = 0
    description: str = ""
    quantity: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    net_amount: float = 0.0
    vat_rate: float = 0.0
    vat_amount: float = 0.0
    gross_amount: float = 0.0


class VatSummaryLine(BaseModel):
    """VAT summary per rate (AFA osszesito soronkent)."""

    vat_rate: float = 0.0
    net_amount: float = 0.0
    vat_amount: float = 0.0
    gross_amount: float = 0.0


class InvoiceTotals(BaseModel):
    """Invoice totals (osszesito)."""

    net_total: float = 0.0
    vat_total: float = 0.0
    gross_total: float = 0.0
    vat_summary: list[VatSummaryLine] = Field(default_factory=list)
    rounding_amount: float = 0.0


class InvoiceValidation(BaseModel):
    """Validation results."""

    is_valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    line_items_sum_matches: bool = True
    vat_calculation_correct: bool = True
    tax_number_format_valid: bool = True
    confidence_score: float = 0.0


class ProcessedInvoice(BaseModel):
    """Complete processed invoice result."""

    source_file: str = ""
    source_directory: str = ""
    direction: str = ""

    vendor: InvoiceParty = Field(default_factory=InvoiceParty)
    buyer: InvoiceParty = Field(default_factory=InvoiceParty)
    header: InvoiceHeader = Field(default_factory=InvoiceHeader)
    line_items: list[LineItem] = Field(default_factory=list)
    totals: InvoiceTotals = Field(default_factory=InvoiceTotals)
    validation: InvoiceValidation = Field(default_factory=InvoiceValidation)

    raw_text: str = ""
    raw_markdown: str = ""
    tables_found: int = 0
    parser_used: str = ""
    processing_time_ms: float = 0.0
    extraction_cost_usd: float = 0.0


class InvoiceBatchResult(BaseModel):
    """Result of batch processing."""

    total_files: int = 0
    processed: int = 0
    failed: int = 0
    invoices: list[ProcessedInvoice] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    total_processing_time_ms: float = 0.0
    total_cost_usd: float = 0.0
