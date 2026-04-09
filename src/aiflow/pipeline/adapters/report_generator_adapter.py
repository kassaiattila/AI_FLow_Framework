"""Pipeline adapter for invoice report generation (Markdown + CSV, no external service)."""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

logger = structlog.get_logger(__name__)

__all__ = [
    "ReportGeneratorInput",
    "ReportGeneratorOutput",
    "ReportSummary",
    "ReportGeneratorAdapter",
]


class InvoiceReportItem(BaseModel):
    """Single invoice entry for the report."""

    invoice_number: str = ""
    vendor_name: str = ""
    amount: float = 0.0
    currency: str = "HUF"
    due_date: str = ""
    payment_status: str = "unknown"
    days_until_due: int = 0
    file_path: str = ""


class ReportGeneratorInput(BaseModel):
    """Input schema for report generation."""

    invoices: list[dict[str, Any]] = Field(default_factory=list)
    payment_statuses: list[dict[str, Any]] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)
    output_dir: str = Field("./data/invoices", description="Output directory for report files")


class ReportSummary(BaseModel):
    """Summary statistics for the report."""

    total_invoices: int = 0
    overdue_count: int = 0
    due_soon_count: int = 0
    not_due_count: int = 0
    unknown_count: int = 0
    total_amount: float = 0.0
    currency: str = "HUF"


class ReportGeneratorOutput(BaseModel):
    """Output schema for report generation."""

    report_markdown: str = ""
    report_path: str = ""
    csv_path: str = ""
    summary: ReportSummary = Field(default_factory=ReportSummary)


def _build_report_items(
    invoices: list[dict[str, Any]],
    payment_statuses: list[dict[str, Any]],
    file_paths: list[str],
) -> list[InvoiceReportItem]:
    """Merge invoice data, payment statuses, and file paths into report items."""
    items: list[InvoiceReportItem] = []
    for i, inv in enumerate(invoices):
        fields = inv.get("fields", inv)
        ps = payment_statuses[i] if i < len(payment_statuses) else {}
        fp = file_paths[i] if i < len(file_paths) else ""

        items.append(
            InvoiceReportItem(
                invoice_number=fields.get("invoice_number", ""),
                vendor_name=fields.get("vendor", {}).get("name", "")
                if isinstance(fields.get("vendor"), dict)
                else fields.get("vendor_name", ""),
                amount=float(
                    fields.get("totals", {}).get("gross_total", 0.0)
                    if isinstance(fields.get("totals"), dict)
                    else fields.get("amount", 0.0)
                ),
                currency=fields.get("currency", "HUF"),
                due_date=fields.get("due_date", ""),
                payment_status=ps.get("payment_status", "unknown"),
                days_until_due=int(ps.get("days_until_due", 0)),
                file_path=fp,
            )
        )
    return items


def _calculate_summary(items: list[InvoiceReportItem]) -> ReportSummary:
    """Calculate summary statistics from report items."""
    summary = ReportSummary(total_invoices=len(items))
    for item in items:
        summary.total_amount += item.amount
        if item.payment_status == "overdue":
            summary.overdue_count += 1
        elif item.payment_status == "due_soon":
            summary.due_soon_count += 1
        elif item.payment_status == "not_due":
            summary.not_due_count += 1
        else:
            summary.unknown_count += 1
    if items:
        summary.currency = items[0].currency
    return summary


def _format_amount(amount: float) -> str:
    """Format amount with thousands separator."""
    if amount == int(amount):
        return f"{int(amount):,}"
    return f"{amount:,.2f}"


def _generate_markdown(items: list[InvoiceReportItem], summary: ReportSummary) -> str:
    """Generate Markdown report from items and summary."""
    today = date.today().isoformat()
    lines: list[str] = []

    lines.append(f"# Invoice Finder Report — {today}")
    lines.append("")

    if not items:
        lines.append("No invoices found.")
        return "\n".join(lines)

    # Summary section
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total invoices:** {summary.total_invoices}")
    lines.append(f"- **Overdue:** {summary.overdue_count}")
    lines.append(f"- **Due soon (30 days):** {summary.due_soon_count}")
    lines.append(f"- **Not due:** {summary.not_due_count}")
    if summary.unknown_count > 0:
        lines.append(f"- **Unknown status:** {summary.unknown_count}")
    lines.append(f"- **Total amount:** {_format_amount(summary.total_amount)} {summary.currency}")
    lines.append("")

    # Detail table
    lines.append("## Invoice Details")
    lines.append("")
    lines.append("| Invoice # | Vendor | Amount | Currency | Due Date | Status |")
    lines.append("|-----------|--------|--------|----------|----------|--------|")
    for item in items:
        status_display = item.payment_status.upper().replace("_", " ")
        lines.append(
            f"| {item.invoice_number} "
            f"| {item.vendor_name} "
            f"| {_format_amount(item.amount)} "
            f"| {item.currency} "
            f"| {item.due_date} "
            f"| {status_display} |"
        )
    lines.append("")

    # Overdue section
    overdue = [it for it in items if it.payment_status == "overdue"]
    if overdue:
        lines.append("## Overdue Invoices")
        lines.append("")
        for item in overdue:
            days = abs(item.days_until_due)
            lines.append(
                f"- **{item.invoice_number}** — {item.vendor_name}: "
                f"{_format_amount(item.amount)} {item.currency} "
                f"({days} days overdue)"
            )
        lines.append("")

    return "\n".join(lines)


def _generate_csv(items: list[InvoiceReportItem]) -> str:
    """Generate CSV content from report items."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "invoice_number",
            "vendor_name",
            "amount",
            "currency",
            "due_date",
            "payment_status",
            "days_until_due",
            "file_path",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.invoice_number,
                item.vendor_name,
                item.amount,
                item.currency,
                item.due_date,
                item.payment_status,
                item.days_until_due,
                item.file_path,
            ]
        )
    return output.getvalue()


class ReportGeneratorAdapter(BaseAdapter):
    """Adapter for generating invoice finder reports (Markdown + CSV).

    This adapter does NOT use an external service — all logic is local
    report generation within the adapter.
    """

    service_name = "report_generator"
    method_name = "generate"
    input_schema = ReportGeneratorInput
    output_schema = ReportGeneratorOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> ReportGeneratorOutput:
        if not isinstance(input_data, ReportGeneratorInput):
            input_data = ReportGeneratorInput.model_validate(input_data)
        data = input_data

        items = _build_report_items(data.invoices, data.payment_statuses, data.file_paths)
        summary = _calculate_summary(items)
        markdown = _generate_markdown(items, summary)
        csv_content = _generate_csv(items)

        # Write files
        output_dir = Path(data.output_dir)
        report_path = str(output_dir / "invoice_finder_report.md")
        csv_path = str(output_dir / "invoices.csv")

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            Path(report_path).write_text(markdown, encoding="utf-8")
            Path(csv_path).write_text(csv_content, encoding="utf-8")
        except OSError as exc:
            logger.warning("report_file_write_failed", error=str(exc))
            report_path = ""
            csv_path = ""

        logger.info(
            "report_generated",
            total_invoices=summary.total_invoices,
            overdue=summary.overdue_count,
            report_path=report_path,
        )

        return ReportGeneratorOutput(
            report_markdown=markdown,
            report_path=report_path,
            csv_path=csv_path,
            summary=summary,
        )


adapter_registry.register(ReportGeneratorAdapter())
