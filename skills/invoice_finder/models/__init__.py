"""Invoice Finder models — I/O types for the invoice finder pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "InvoiceEmailResult",
    "InvoiceEmailSearchOutput",
    "AcquiredDocument",
    "DocumentAcquisitionOutput",
    "InvoiceClassificationResult",
    "PaymentStatus",
    "ReportResult",
]


class InvoiceEmailResult(BaseModel):
    """Single email result from invoice-focused mailbox scan."""

    email_id: str = ""
    subject: str = ""
    sender: str = ""
    date: str = ""
    score: float = 0.0
    has_attachment: bool = False
    attachment_names: list[str] = Field(default_factory=list)
    body_snippet: str = ""


class InvoiceEmailSearchOutput(BaseModel):
    """Output of the email search step."""

    emails: list[InvoiceEmailResult] = Field(default_factory=list)
    total_scanned: int = 0
    total_matched: int = 0
    connector_id: str = ""


class AcquiredDocument(BaseModel):
    """A document acquired from an email (attachment or URL)."""

    email_id: str = ""
    file_name: str = ""
    file_path: str = ""
    raw_text: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    page_count: int = 0
    parser_used: str = ""
    quality_score: float = 0.0
    source: str = ""  # "attachment" | "url" | "body"


class DocumentAcquisitionOutput(BaseModel):
    """Output of the document acquisition step."""

    documents: list[AcquiredDocument] = Field(default_factory=list)
    total_acquired: int = 0
    total_skipped: int = 0


class InvoiceClassificationResult(BaseModel):
    """Classification result for a single document."""

    email_id: str = ""
    file_name: str = ""
    is_invoice: bool = False
    confidence: float = 0.0
    doc_type: str = ""
    language: str = ""
    needs_review: bool = False


class PaymentStatus(BaseModel):
    """Payment status result for a single invoice."""

    invoice_number: str = ""
    due_date: str = ""
    amount: float = 0.0
    payment_status: str = Field("unknown", description="overdue | due_soon | not_due | unknown")
    days_until_due: int = 0
    is_overdue: bool = False


class ReportResult(BaseModel):
    """Result of the invoice finder report generation."""

    report_markdown: str = ""
    report_path: str = ""
    csv_path: str = ""
    total_invoices: int = 0
    overdue_count: int = 0
    due_soon_count: int = 0
    total_amount: float = 0.0
