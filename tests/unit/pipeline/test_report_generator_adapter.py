"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.report_generator_adapter
    covers: [src/aiflow/pipeline/adapters/report_generator_adapter.py]
    phase: B3
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [pipeline, adapter, invoice-finder, report]
"""

from __future__ import annotations

import csv
import io

import pytest

from aiflow.pipeline.adapters.report_generator_adapter import (
    InvoiceReportItem,
    _calculate_summary,
    _generate_csv,
    _generate_markdown,
)


def _sample_items() -> list[InvoiceReportItem]:
    """Create sample invoice report items for testing."""
    return [
        InvoiceReportItem(
            invoice_number="INV-2026-001",
            vendor_name="Test Kft.",
            amount=127000.0,
            currency="HUF",
            due_date="2026-03-01",
            payment_status="overdue",
            days_until_due=-36,
            file_path="/data/invoices/test_kft/INV-2026-001.pdf",
        ),
        InvoiceReportItem(
            invoice_number="INV-2026-002",
            vendor_name="Pelda Zrt.",
            amount=254000.0,
            currency="HUF",
            due_date="2026-04-20",
            payment_status="due_soon",
            days_until_due=14,
            file_path="/data/invoices/pelda_zrt/INV-2026-002.pdf",
        ),
        InvoiceReportItem(
            invoice_number="INV-2026-003",
            vendor_name="Remote LLC",
            amount=500.0,
            currency="USD",
            due_date="2026-07-01",
            payment_status="not_due",
            days_until_due=86,
            file_path="/data/invoices/remote_llc/INV-2026-003.pdf",
        ),
    ]


class TestReportMarkdownStructure:
    """Report generator: Markdown output has correct structure."""

    def test_report_markdown_structure(self) -> None:
        """Markdown report has header, summary section, and detail table."""
        items = _sample_items()
        summary = _calculate_summary(items)
        md = _generate_markdown(items, summary)

        # Header
        assert "# Invoice Finder Report" in md
        # Summary section
        assert "## Summary" in md
        assert "**Total invoices:** 3" in md
        assert "**Overdue:** 1" in md
        assert "**Due soon" in md
        # Detail table headers
        assert "| Invoice #" in md
        assert "| Vendor" in md
        assert "| Amount" in md
        assert "| Status |" in md
        # Overdue section
        assert "## Overdue Invoices" in md
        assert "INV-2026-001" in md


class TestReportCsvGeneration:
    """Report generator: CSV output has correct columns and data."""

    def test_report_csv_generation(self) -> None:
        """CSV contains correct headers and rows for each invoice."""
        items = _sample_items()
        csv_content = _generate_csv(items)

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Header row
        assert rows[0] == [
            "invoice_number",
            "vendor_name",
            "amount",
            "currency",
            "due_date",
            "payment_status",
            "days_until_due",
            "file_path",
        ]
        # Data rows
        assert len(rows) == 4  # header + 3 items
        assert rows[1][0] == "INV-2026-001"
        assert rows[2][0] == "INV-2026-002"
        assert rows[3][0] == "INV-2026-003"
        assert rows[1][5] == "overdue"
        assert rows[2][5] == "due_soon"


class TestReportSummaryCalculation:
    """Report generator: summary statistics are correct."""

    def test_report_summary_calculation(self) -> None:
        """Summary counts and total amount are correctly computed."""
        items = _sample_items()
        summary = _calculate_summary(items)

        assert summary.total_invoices == 3
        assert summary.overdue_count == 1
        assert summary.due_soon_count == 1
        assert summary.not_due_count == 1
        assert summary.unknown_count == 0
        assert summary.total_amount == pytest.approx(127000.0 + 254000.0 + 500.0)


class TestReportEmptyInput:
    """Report generator: handles empty invoice list."""

    def test_report_empty_input(self) -> None:
        """Empty invoice list produces 'No invoices found' report."""
        items: list[InvoiceReportItem] = []
        summary = _calculate_summary(items)
        md = _generate_markdown(items, summary)

        assert "# Invoice Finder Report" in md
        assert "No invoices found." in md
        assert summary.total_invoices == 0
        assert summary.total_amount == 0.0


class TestReportPaymentStatusDisplay:
    """Report generator: payment statuses display correctly in the table."""

    def test_report_payment_status_display(self) -> None:
        """Payment status values appear uppercased with underscores replaced."""
        items = _sample_items()
        summary = _calculate_summary(items)
        md = _generate_markdown(items, summary)

        assert "OVERDUE" in md
        assert "DUE SOON" in md
        assert "NOT DUE" in md
