"""Invoice processing workflow - parse, classify, extract, validate, store, export.

Pipeline: parse_invoice -> classify_invoice -> extract_invoice_data
       -> validate_invoice -> store_invoice -> export_invoice
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import structlog
from skills.invoice_processor import models_client, prompt_manager
from skills.invoice_processor.models import (
    InvoiceHeader,
    InvoiceParty,
    InvoiceTotals,
    InvoiceValidation,
    LineItem,
    ProcessedInvoice,
    VatSummaryLine,
)

from aiflow.engine.step import step

__all__ = [
    "parse_invoice",
    "classify_invoice",
    "extract_invoice_data",
    "validate_invoice",
    "store_invoice",
    "export_invoice",
]

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff"}


# ---------------------------------------------------------------------------
# Step 1: Parse PDF
# ---------------------------------------------------------------------------

@step(name="parse_invoice", description="Parse PDF invoices into raw text")
async def parse_invoice(data: dict) -> dict:
    """Parse PDF files from source path using DoclingParser.

    Input:
        source_path: str - single PDF or directory of PDFs
        direction: str - "incoming", "outgoing", or "auto" (default: auto)

    Output:
        files: list[dict] - parsed files with raw_text, markdown, tables
        direction_hint: str - from input or path detection
    """
    source = Path(data.get("source_path", data.get("source", "")))
    direction = data.get("direction", "auto")

    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    # Collect PDF files
    if source.is_file():
        pdf_files = [source]
    else:
        pdf_files = sorted(
            f for f in source.rglob("*")
            if f.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    if not pdf_files:
        raise ValueError(f"No supported files found in {source}")

    # Parse each file
    parsed_files: list[dict[str, Any]] = []
    for pdf_path in pdf_files:
        try:
            parsed = await _parse_single_pdf(pdf_path)
            parsed_files.append(parsed)
        except Exception as exc:
            logger.warning("parse_invoice.file_error", file=str(pdf_path), error=str(exc))
            parsed_files.append({
                "path": str(pdf_path),
                "filename": pdf_path.name,
                "raw_text": "",
                "raw_markdown": "",
                "tables": [],
                "parser_used": "failed",
                "error": str(exc),
            })

    logger.info("parse_invoice.done", total=len(pdf_files), parsed=len(parsed_files))

    return {
        "files": parsed_files,
        "direction_hint": direction,
        "source_path": str(source),
    }


def _parse_single_pdf_sync(pdf_path: Path) -> dict[str, Any]:
    """Parse a single PDF with DoclingParser, fallback to PyMuPDF (sync)."""
    docling_error = None

    try:
        from aiflow.ingestion.parsers.docling_parser import DoclingParser

        parser = DoclingParser()
        logger.info("docling_parse_start", file=pdf_path.name, size_kb=round(pdf_path.stat().st_size / 1024))
        result = parser.parse(str(pdf_path))
        return {
            "path": str(pdf_path),
            "filename": pdf_path.name,
            "raw_text": result.text,
            "raw_markdown": result.markdown,
            "tables": [t.model_dump() for t in result.tables] if result.tables else [],
            "parser_used": "docling",
            "file_size_kb": pdf_path.stat().st_size / 1024,
        }
    except Exception as exc:
        docling_error = str(exc)
        logger.info("parse_invoice.docling_fallback", file=pdf_path.name, error=docling_error)

    # Fallback: pypdfium2 (text extraction)
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(pdf_path))
        text = "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
        doc.close()
        logger.info("parse_invoice.pypdfium2_ok", file=pdf_path.name, chars=len(text))
        return {
            "path": str(pdf_path),
            "filename": pdf_path.name,
            "raw_text": text,
            "raw_markdown": "",
            "tables": [],
            "parser_used": "pypdfium2",
            "file_size_kb": pdf_path.stat().st_size / 1024,
        }
    except Exception as pdfium_err:
        raise RuntimeError(f"All parsers failed for {pdf_path.name}: docling={docling_error}, pypdfium2={pdfium_err}")


async def _parse_single_pdf(pdf_path: Path) -> dict[str, Any]:
    """Parse a single PDF — runs blocking Docling/fitz in a thread."""
    return await asyncio.to_thread(_parse_single_pdf_sync, pdf_path)


# ---------------------------------------------------------------------------
# Step 2: Classify (incoming vs outgoing)
# ---------------------------------------------------------------------------

@step(name="classify_invoice", description="Classify invoices as incoming or outgoing")
async def classify_invoice(data: dict) -> dict:
    """Classify each invoice as incoming (bejovo) or outgoing (kimeno).

    Uses heuristics first (path, filename), LLM fallback if uncertain.
    """
    files = data.get("files", [])
    direction_hint = data.get("direction_hint", "auto")

    for f in files:
        if direction_hint in ("incoming", "outgoing"):
            f["direction"] = direction_hint
            f["classify_method"] = "manual"
            continue

        # Heuristic 1: path-based
        path_lower = f.get("path", "").lower()
        if "bejov" in path_lower or "incoming" in path_lower:
            f["direction"] = "incoming"
            f["classify_method"] = "path_heuristic"
            continue
        if "kimen" in path_lower or "outgoing" in path_lower:
            f["direction"] = "outgoing"
            f["classify_method"] = "path_heuristic"
            continue

        # Heuristic 2: filename prefix
        filename = f.get("filename", "")
        if filename.startswith(("BD", "BESE")):
            f["direction"] = "outgoing"
            f["classify_method"] = "filename_heuristic"
            continue

        # Heuristic 3: text content check for BestIx
        text = f.get("raw_text", "").lower()
        if "bestix" in text or "bestixcom" in text:
            if re.search(r"sz[aá]ll[ií]t[oó].*bestix", text, re.IGNORECASE | re.DOTALL):
                f["direction"] = "outgoing"
                f["classify_method"] = "text_heuristic"
                continue
            if re.search(r"vev[oő].*bestix", text, re.IGNORECASE | re.DOTALL):
                f["direction"] = "incoming"
                f["classify_method"] = "text_heuristic"
                continue

        # LLM fallback
        f["direction"] = await _classify_with_llm(f.get("raw_text", ""))
        f["classify_method"] = "llm"

    logger.info(
        "classify_invoice.done",
        incoming=sum(1 for f in files if f.get("direction") == "incoming"),
        outgoing=sum(1 for f in files if f.get("direction") == "outgoing"),
    )
    return data


async def _classify_with_llm(text: str) -> str:
    """Use LLM to classify invoice direction."""
    try:
        prompt = prompt_manager.get("invoice/classifier")
        messages = prompt.compile(variables={"invoice_text": text[:3000]})
        result = await models_client.generate(
            messages=messages,
            model=prompt.config.model,
            temperature=prompt.config.temperature,
            max_tokens=prompt.config.max_tokens,
        )
        parsed = json.loads(result.output.text)
        return parsed.get("direction", "incoming")
    except Exception as exc:
        logger.warning("classify_llm_error", error=str(exc))
        return "incoming"


# ---------------------------------------------------------------------------
# Step 3: Extract structured data (2 LLM calls)
# ---------------------------------------------------------------------------

@step(name="extract_invoice_data", description="Extract structured invoice fields via LLM")
async def extract_invoice_data(data: dict) -> dict:
    """Extract header, line items, and totals from each invoice.

    Uses two focused LLM calls:
    1. Header: vendor, buyer, dates, payment
    2. Line items + totals
    """
    files = data.get("files", [])

    for f in files:
        if f.get("error"):
            continue

        text = f.get("raw_text", "")
        tables_md = f.get("raw_markdown", "")
        start = time.monotonic()

        # Run both LLM calls in parallel — no data dependency between them
        header_data, lines_data = await asyncio.gather(
            _extract_header(text),
            _extract_lines(text, tables_md),
        )

        f["vendor"] = header_data.get("vendor", {})
        f["buyer"] = header_data.get("buyer", {})
        f["header"] = header_data.get("header", {})
        f["line_items"] = lines_data.get("line_items", [])
        f["totals"] = lines_data.get("totals", {})
        f["extraction_time_ms"] = round((time.monotonic() - start) * 1000, 1)

        # Merge confidence from both LLM calls (average)
        header_conf = float(header_data.get("confidence", 0.5))
        lines_conf = float(lines_data.get("confidence", 0.5))
        f["extraction_confidence"] = round((header_conf + lines_conf) / 2, 3)

        # Collect LLM token usage for cost tracking
        h_usage = header_data.pop("_llm_usage", {})
        l_usage = lines_data.pop("_llm_usage", {})
        f["_llm_total_input_tokens"] = h_usage.get("input_tokens", 0) + l_usage.get("input_tokens", 0)
        f["_llm_total_output_tokens"] = h_usage.get("output_tokens", 0) + l_usage.get("output_tokens", 0)
        f["_llm_model"] = h_usage.get("model", "openai/gpt-4o")

        logger.info(
            "extract_invoice.done",
            file=f.get("filename"),
            vendor=f["vendor"].get("name", "?"),
            buyer=f["buyer"].get("name", "?"),
            currency=f["header"].get("currency", "?"),
            items=len(f["line_items"]),
            gross=f["totals"].get("gross_total", 0),
            confidence=f["extraction_confidence"],
            input_tokens=f["_llm_total_input_tokens"],
            output_tokens=f["_llm_total_output_tokens"],
        )

    return data


async def _extract_header(text: str) -> dict[str, Any]:
    """Extract header fields via LLM."""
    try:
        prompt = prompt_manager.get("invoice/header_extractor")
        messages = prompt.compile(variables={"invoice_text": text[:4000]})
        result = await models_client.generate(
            messages=messages,
            model=prompt.config.model,
            temperature=prompt.config.temperature,
            max_tokens=prompt.config.max_tokens,
        )
        parsed = _parse_json_response(result.output.text, "header")
        parsed["_llm_usage"] = {
            "model": prompt.config.model,
            "input_tokens": getattr(result, "input_tokens", 0),
            "output_tokens": getattr(result, "output_tokens", 0),
        }
        return parsed
    except Exception as exc:
        logger.warning("extract_header_error", error=str(exc))
        return {"vendor": {}, "buyer": {}, "header": {}}


async def _extract_lines(text: str, tables_md: str) -> dict[str, Any]:
    """Extract line items and totals via LLM."""
    try:
        prompt = prompt_manager.get("invoice/line_extractor")
        messages = prompt.compile(variables={
            "invoice_text": text[:5000],
            "tables_markdown": tables_md[:2000] if tables_md else "",
        })
        result = await models_client.generate(
            messages=messages,
            model=prompt.config.model,
            temperature=prompt.config.temperature,
            max_tokens=prompt.config.max_tokens,
        )
        parsed = _parse_json_response(result.output.text, "lines")
        parsed["_llm_usage"] = {
            "model": prompt.config.model,
            "input_tokens": getattr(result, "input_tokens", 0),
            "output_tokens": getattr(result, "output_tokens", 0),
        }
        return parsed
    except Exception as exc:
        logger.warning("extract_lines_error", error=str(exc))
        return {"line_items": [], "totals": {}}


def _parse_json_response(text: str, context: str = "") -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    # Strip markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        logger.warning("json_parse_failed", context=context, text_preview=text[:200])
        return {}


# ---------------------------------------------------------------------------
# Step 4: Validate (pure Python)
# ---------------------------------------------------------------------------

@step(name="validate_invoice", description="Cross-check extracted invoice data")
async def validate_invoice(data: dict) -> dict:
    """Validate extracted data: sum checks, VAT, required fields."""
    files = data.get("files", [])
    tolerance = 2.0  # HUF tolerance for rounding

    for f in files:
        if f.get("error"):
            continue

        errors: list[str] = []
        warnings: list[str] = []
        line_items = f.get("line_items", [])
        totals = f.get("totals", {})
        header = f.get("header", {})
        vendor = f.get("vendor", {})
        buyer = f.get("buyer", {})

        # Required fields
        if not header.get("invoice_number"):
            errors.append("Hianyzik: szamlaszam")
        if not vendor.get("name"):
            errors.append("Hianyzik: szallito neve")
        if not buyer.get("name"):
            errors.append("Hianyzik: vevo neve")
        if not line_items:
            errors.append("Nincsenek tetelek")

        # Tax number format
        tax_re = re.compile(r"^\d{8}-\d-\d{2}$")
        for party_name, party in [("szallito", vendor), ("vevo", buyer)]:
            tn = party.get("tax_number", "")
            if tn and not tax_re.match(tn):
                warnings.append(f"{party_name} adoszam formatum hibas: {tn}")

        # Line items sum vs totals
        if line_items and totals.get("net_total"):
            sum_net = sum(item.get("net_amount", 0) for item in line_items)
            sum_vat = sum(item.get("vat_amount", 0) for item in line_items)
            sum_gross = sum(item.get("gross_amount", 0) for item in line_items)

            if abs(sum_net - totals.get("net_total", 0)) > tolerance:
                errors.append(
                    f"Netto osszeg elter: tetelek={sum_net:.0f}, osszesito={totals['net_total']:.0f}"
                )
            if abs(sum_vat - totals.get("vat_total", 0)) > tolerance:
                warnings.append(
                    f"AFA osszeg elter: tetelek={sum_vat:.0f}, osszesito={totals.get('vat_total', 0):.0f}"
                )
            if abs(sum_gross - totals.get("gross_total", 0)) > tolerance:
                warnings.append(
                    f"Brutto osszeg elter: tetelek={sum_gross:.0f}, osszesito={totals.get('gross_total', 0):.0f}"
                )

        # Per-line VAT check
        vat_ok = True
        for item in line_items:
            expected_vat = item.get("net_amount", 0) * item.get("vat_rate", 0) / 100
            if abs(expected_vat - item.get("vat_amount", 0)) > tolerance:
                vat_ok = False
                break

        confidence = 1.0
        if errors:
            confidence -= 0.2 * len(errors)
        if warnings:
            confidence -= 0.05 * len(warnings)

        f["validation"] = {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "line_items_sum_matches": "Netto osszeg elter" not in str(errors),
            "vat_calculation_correct": vat_ok,
            "tax_number_format_valid": "adoszam formatum" not in str(warnings),
            "confidence_score": round(max(0.0, min(1.0, confidence)), 3),
        }

    valid = sum(1 for f in files if f.get("validation", {}).get("is_valid", False))
    logger.info("validate_invoice.done", valid=valid, total=len(files))
    return data


# ---------------------------------------------------------------------------
# Step 5: Store to PostgreSQL
# ---------------------------------------------------------------------------

def _parse_date(val: str | None) -> object | None:
    """Parse a YYYY-MM-DD string to datetime.date, or return None."""
    if not val:
        return None
    try:
        from datetime import date as _date
        parts = val.strip().split("-")
        if len(parts) == 3:
            return _date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError):
        pass
    return None


@step(name="store_invoice", description="Persist extracted invoices to database")
async def store_invoice(data: dict) -> dict:
    """Store invoices and line items in PostgreSQL (best-effort)."""
    import os
    files = data.get("files", [])

    db_url = os.getenv(
        "AIFLOW_DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )

    for f in files:
        if f.get("error"):
            continue
        try:
            import asyncpg
            conn = await asyncpg.connect(db_url)
            try:
                raw_text = f.get("raw_text", "")
                text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

                invoice_id = await conn.fetchval(
                    """
                    INSERT INTO invoices (
                        direction, source_file, source_directory,
                        vendor_name, vendor_address, vendor_tax_number, vendor_bank_account, vendor_bank_name,
                        buyer_name, buyer_address, buyer_tax_number,
                        invoice_number, invoice_date, fulfillment_date, due_date,
                        currency, payment_method, invoice_type,
                        net_total, vat_total, gross_total, rounding_amount,
                        vat_summary, is_valid, validation_errors, confidence_score,
                        parser_used, raw_text_hash, customer
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22,
                        $23::jsonb, $24, $25::jsonb, $26,
                        $27, $28, $29
                    )
                    ON CONFLICT (source_file, raw_text_hash) DO NOTHING
                    RETURNING id
                    """,
                    f.get("direction", ""),
                    f.get("path", ""),
                    data.get("source_path", ""),
                    f.get("vendor", {}).get("name", ""),
                    f.get("vendor", {}).get("address", ""),
                    f.get("vendor", {}).get("tax_number", ""),
                    f.get("vendor", {}).get("bank_account", ""),
                    f.get("vendor", {}).get("bank_name", ""),
                    f.get("buyer", {}).get("name", ""),
                    f.get("buyer", {}).get("address", ""),
                    f.get("buyer", {}).get("tax_number", ""),
                    f.get("header", {}).get("invoice_number", ""),
                    _parse_date(f.get("header", {}).get("invoice_date")),
                    _parse_date(f.get("header", {}).get("fulfillment_date")),
                    _parse_date(f.get("header", {}).get("due_date")),
                    f.get("header", {}).get("currency", "HUF"),
                    f.get("header", {}).get("payment_method", ""),
                    f.get("header", {}).get("invoice_type", "szamla"),
                    f.get("totals", {}).get("net_total", 0),
                    f.get("totals", {}).get("vat_total", 0),
                    f.get("totals", {}).get("gross_total", 0),
                    f.get("totals", {}).get("rounding_amount", 0),
                    json.dumps(f.get("totals", {}).get("vat_summary", [])),
                    f.get("validation", {}).get("is_valid", True),
                    json.dumps(f.get("validation", {}).get("errors", [])),
                    f.get("validation", {}).get("confidence_score", 0),
                    f.get("parser_used", ""),
                    text_hash,
                    "bestix",
                )

                if invoice_id:
                    for item in f.get("line_items", []):
                        await conn.execute(
                            """
                            INSERT INTO invoice_line_items (
                                invoice_id, line_number, description, quantity, unit,
                                unit_price, net_amount, vat_rate, vat_amount, gross_amount
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                            """,
                            invoice_id,
                            item.get("line_number", 0),
                            item.get("description", ""),
                            item.get("quantity", 0),
                            item.get("unit", ""),
                            item.get("unit_price", 0),
                            item.get("net_amount", 0),
                            item.get("vat_rate", 0),
                            item.get("vat_amount", 0),
                            item.get("gross_amount", 0),
                        )
                    f["db_invoice_id"] = str(invoice_id)
                    logger.info("store_invoice.saved", file=f.get("filename"), id=str(invoice_id))
                else:
                    f["db_invoice_id"] = "duplicate"
            finally:
                await conn.close()
        except Exception as exc:
            logger.warning("store_invoice.error", file=f.get("filename"), error=str(exc))
            f["db_error"] = str(exc)

    return data


# ---------------------------------------------------------------------------
# Step 6: Export
# ---------------------------------------------------------------------------

@step(name="export_invoice", description="Export processed invoices to CSV/Excel/JSON")
async def export_invoice(data: dict) -> dict:
    """Export processed invoice data to files.

    All files are written to a local temp directory first, then copied
    to the final output_dir in one batch. This avoids slow per-file I/O
    on network-synced drives (OneDrive, SharePoint, Google Drive).
    """
    import shutil
    import tempfile

    files = data.get("files", [])
    output_dir = Path(data.get("output_dir", data.get("output", "./test_output/invoices")))
    output_dir.mkdir(parents=True, exist_ok=True)
    export_format = data.get("format", "all")

    invoices = _build_invoice_objects(files)
    exported: list[str] = []

    # Write everything to a fast local temp dir first
    tmp_dir = Path(tempfile.mkdtemp(prefix="aiflow_export_"))

    try:
        if export_format in ("csv", "all"):
            _export_csv(invoices, tmp_dir / "invoices.csv")
            exported.append("invoices.csv")

        if export_format in ("json", "all"):
            json_str = json.dumps(
                [inv.model_dump(mode="json") for inv in invoices],
                ensure_ascii=False, indent=2,
            )
            (tmp_dir / "invoices.json").write_text(json_str, encoding="utf-8")
            exported.append("invoices.json")

        if export_format in ("excel", "all"):
            try:
                _export_excel(invoices, tmp_dir / "invoices.xlsx")
                exported.append("invoices.xlsx")
            except ImportError:
                logger.warning("export_invoice.openpyxl_missing")

        # Single batch copy from local temp → final output (one network round-trip per file)
        for fname in exported:
            shutil.copy2(str(tmp_dir / fname), str(output_dir / fname))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info("export_invoice.done", files=len(exported), invoices=len(invoices))

    return {
        **data,
        "exported_files": [str(output_dir / f) for f in exported],
        "export_summary": {
            "total_invoices": len(invoices),
            "total_line_items": sum(len(inv.line_items) for inv in invoices),
            "total_gross": sum(inv.totals.gross_total for inv in invoices),
        },
    }


def _build_invoice_objects(files: list[dict]) -> list[ProcessedInvoice]:
    """Convert raw file dicts to ProcessedInvoice objects."""
    invoices: list[ProcessedInvoice] = []
    for f in files:
        if f.get("error"):
            continue
        invoices.append(ProcessedInvoice(
            source_file=f.get("filename", ""),
            source_directory=f.get("path", ""),
            direction=f.get("direction", ""),
            vendor=InvoiceParty(**f.get("vendor", {})),
            buyer=InvoiceParty(**f.get("buyer", {})),
            header=InvoiceHeader(**f.get("header", {})),
            line_items=[LineItem(**item) for item in f.get("line_items", [])],
            totals=InvoiceTotals(
                **{k: v for k, v in f.get("totals", {}).items() if k != "vat_summary"},
                vat_summary=[VatSummaryLine(**vs) for vs in f.get("totals", {}).get("vat_summary", [])],
            ),
            validation=InvoiceValidation(**f.get("validation", {})),
            tables_found=len(f.get("tables", [])),
            parser_used=f.get("parser_used", ""),
        ))
    return invoices


def _export_csv(invoices: list[ProcessedInvoice], path: Path) -> None:
    """Export invoices to CSV (one row per line item, denormalized header).

    Buffered in memory with io.StringIO then written in a single operation
    to avoid slow row-by-row I/O on network-synced drives (OneDrive).
    """
    import io

    fields = [
        "source_file", "direction", "invoice_number", "invoice_date", "due_date",
        "vendor_name", "vendor_tax_number", "buyer_name", "buyer_tax_number",
        "currency", "payment_method",
        "line_number", "description", "quantity", "unit", "unit_price",
        "net_amount", "vat_rate", "vat_amount", "gross_amount",
        "net_total", "vat_total", "gross_total", "is_valid",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, delimiter=";")
    writer.writeheader()
    for inv in invoices:
        base = {
            "source_file": inv.source_file,
            "direction": inv.direction,
            "invoice_number": inv.header.invoice_number,
            "invoice_date": inv.header.invoice_date,
            "due_date": inv.header.due_date,
            "vendor_name": inv.vendor.name,
            "vendor_tax_number": inv.vendor.tax_number,
            "buyer_name": inv.buyer.name,
            "buyer_tax_number": inv.buyer.tax_number,
            "currency": inv.header.currency,
            "payment_method": inv.header.payment_method,
            "net_total": inv.totals.net_total,
            "vat_total": inv.totals.vat_total,
            "gross_total": inv.totals.gross_total,
            "is_valid": inv.validation.is_valid,
        }
        if inv.line_items:
            for item in inv.line_items:
                writer.writerow({
                    **base,
                    "line_number": item.line_number,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "net_amount": item.net_amount,
                    "vat_rate": item.vat_rate,
                    "vat_amount": item.vat_amount,
                    "gross_amount": item.gross_amount,
                })
        else:
            writer.writerow(base)
    # Single atomic write — avoids row-by-row I/O on network drives
    path.write_text(buf.getvalue(), encoding="utf-8-sig")


def _export_excel(invoices: list[ProcessedInvoice], path: Path) -> None:
    """Export invoices to Excel with two sheets."""
    from openpyxl import Workbook

    wb = Workbook()

    # Sheet 1: Summary
    ws_sum = wb.active
    ws_sum.title = "Osszesito"
    sum_headers = [
        "Fajl", "Irany", "Szamlaszam", "Datum", "Hat.ido",
        "Szallito", "Ado.sz.", "Vevo", "Ado.sz.",
        "Netto", "AFA", "Brutto", "Penznem", "Valid",
    ]
    ws_sum.append(sum_headers)
    for inv in invoices:
        ws_sum.append([
            inv.source_file, inv.direction,
            inv.header.invoice_number, inv.header.invoice_date, inv.header.due_date,
            inv.vendor.name, inv.vendor.tax_number,
            inv.buyer.name, inv.buyer.tax_number,
            inv.totals.net_total, inv.totals.vat_total, inv.totals.gross_total,
            inv.header.currency, inv.validation.is_valid,
        ])

    # Sheet 2: Line Items
    ws_items = wb.create_sheet("Tetelek")
    item_headers = [
        "Szamlaszam", "Szallito", "Sor", "Megnevezes",
        "Menny.", "Egyseg", "Egysegar", "Netto", "AFA%", "AFA", "Brutto",
    ]
    ws_items.append(item_headers)
    for inv in invoices:
        for item in inv.line_items:
            ws_items.append([
                inv.header.invoice_number, inv.vendor.name,
                item.line_number, item.description,
                item.quantity, item.unit, item.unit_price,
                item.net_amount, item.vat_rate, item.vat_amount, item.gross_amount,
            ])

    wb.save(str(path))
