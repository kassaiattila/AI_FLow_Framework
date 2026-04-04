"""
@test_registry:
    suite: invoice-processor-unit
    component: skills.invoice_processor.workflows
    covers:
        - skills/invoice_processor/workflows/process.py
        - skills/invoice_processor/models/__init__.py
    phase: 4
    priority: high
    estimated_duration_ms: 2000
    requires_services: []
    tags: [invoice, extraction, validation, hungarian]
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from skills.invoice_processor.models import (
    InvoiceBatchResult,
    InvoiceHeader,
    InvoiceParty,
    InvoiceTotals,
    InvoiceValidation,
    LineItem,
    ProcessedInvoice,
    VatSummaryLine,
)

# ── Model Tests ─────────────────────────────────────────────────────────────


class TestModels:
    def test_invoice_party(self):
        p = InvoiceParty(name="BestIx Kft", tax_number="12345678-2-41")
        assert p.name == "BestIx Kft"
        assert p.bank_account == ""

    def test_invoice_header_defaults(self):
        h = InvoiceHeader()
        assert h.currency == "HUF"
        assert h.invoice_type == "szamla"
        assert h.language == "hu"

    def test_line_item(self):
        item = LineItem(
            line_number=1, description="Szoftver licenc",
            quantity=1, unit="db", unit_price=10000,
            net_amount=10000, vat_rate=27, vat_amount=2700, gross_amount=12700,
        )
        assert item.gross_amount == 12700

    def test_vat_summary_line(self):
        vs = VatSummaryLine(vat_rate=27, net_amount=10000, vat_amount=2700, gross_amount=12700)
        assert vs.vat_rate == 27

    def test_invoice_totals(self):
        t = InvoiceTotals(net_total=10000, vat_total=2700, gross_total=12700)
        assert t.gross_total == 12700

    def test_validation_defaults(self):
        v = InvoiceValidation()
        assert v.is_valid is True
        assert v.errors == []

    def test_processed_invoice(self):
        inv = ProcessedInvoice(
            source_file="test.pdf",
            direction="incoming",
            vendor=InvoiceParty(name="Vendor Kft"),
            buyer=InvoiceParty(name="BestIx Kft"),
        )
        assert inv.direction == "incoming"
        assert inv.vendor.name == "Vendor Kft"

    def test_batch_result(self):
        br = InvoiceBatchResult(total_files=5, processed=4, failed=1)
        assert br.failed == 1


# ── Classify Tests ──────────────────────────────────────────────────────────


class TestClassifyInvoice:
    @pytest.mark.asyncio
    async def test_path_based_incoming(self):
        from skills.invoice_processor.workflows.process import classify_invoice

        result = await classify_invoice({
            "files": [{"path": "C:/Szamlak/Bejovo/2021/test.pdf", "filename": "test.pdf", "raw_text": "text"}],
            "direction_hint": "auto",
        })
        assert result["files"][0]["direction"] == "incoming"
        assert result["files"][0]["classify_method"] == "path_heuristic"

    @pytest.mark.asyncio
    async def test_path_based_outgoing(self):
        from skills.invoice_processor.workflows.process import classify_invoice

        result = await classify_invoice({
            "files": [{"path": "C:/Szamlak/Kimeno/BD001.pdf", "filename": "BD001.pdf", "raw_text": "text"}],
            "direction_hint": "auto",
        })
        assert result["files"][0]["direction"] == "outgoing"

    @pytest.mark.asyncio
    async def test_filename_prefix_outgoing(self):
        from skills.invoice_processor.workflows.process import classify_invoice

        result = await classify_invoice({
            "files": [{"path": "/tmp/BD001_Ecory.pdf", "filename": "BD001_Ecory.pdf", "raw_text": "text"}],
            "direction_hint": "auto",
        })
        assert result["files"][0]["direction"] == "outgoing"
        assert result["files"][0]["classify_method"] == "filename_heuristic"

    @pytest.mark.asyncio
    async def test_manual_direction(self):
        from skills.invoice_processor.workflows.process import classify_invoice

        result = await classify_invoice({
            "files": [{"path": "unknown.pdf", "filename": "unknown.pdf", "raw_text": "text"}],
            "direction_hint": "incoming",
        })
        assert result["files"][0]["direction"] == "incoming"
        assert result["files"][0]["classify_method"] == "manual"


# ── Validate Tests ──────────────────────────────────────────────────────────


class TestValidateInvoice:
    @pytest.mark.asyncio
    async def test_valid_invoice(self):
        from skills.invoice_processor.workflows.process import validate_invoice

        result = await validate_invoice({
            "files": [{
                "vendor": {"name": "Vendor Kft", "tax_number": "12345678-2-41"},
                "buyer": {"name": "BestIx Kft", "tax_number": "87654321-2-41"},
                "header": {"invoice_number": "INV-001"},
                "line_items": [
                    {"net_amount": 10000, "vat_rate": 27, "vat_amount": 2700, "gross_amount": 12700},
                ],
                "totals": {"net_total": 10000, "vat_total": 2700, "gross_total": 12700},
            }],
        })
        validation = result["files"][0]["validation"]
        assert validation["is_valid"] is True
        assert validation["line_items_sum_matches"] is True
        assert validation["vat_calculation_correct"] is True

    @pytest.mark.asyncio
    async def test_missing_invoice_number(self):
        from skills.invoice_processor.workflows.process import validate_invoice

        result = await validate_invoice({
            "files": [{
                "vendor": {"name": "V"}, "buyer": {"name": "B"},
                "header": {"invoice_number": ""},
                "line_items": [{"net_amount": 100, "vat_rate": 27, "vat_amount": 27, "gross_amount": 127}],
                "totals": {"net_total": 100, "vat_total": 27, "gross_total": 127},
            }],
        })
        assert result["files"][0]["validation"]["is_valid"] is False
        assert "szamlaszam" in result["files"][0]["validation"]["errors"][0].lower()

    @pytest.mark.asyncio
    async def test_sum_mismatch(self):
        from skills.invoice_processor.workflows.process import validate_invoice

        result = await validate_invoice({
            "files": [{
                "vendor": {"name": "V"}, "buyer": {"name": "B"},
                "header": {"invoice_number": "X-001"},
                "line_items": [
                    {"net_amount": 10000, "vat_rate": 27, "vat_amount": 2700, "gross_amount": 12700},
                ],
                "totals": {"net_total": 99999, "vat_total": 2700, "gross_total": 12700},
            }],
        })
        assert result["files"][0]["validation"]["is_valid"] is False

    @pytest.mark.asyncio
    async def test_bad_tax_number_format(self):
        from skills.invoice_processor.workflows.process import validate_invoice

        result = await validate_invoice({
            "files": [{
                "vendor": {"name": "V", "tax_number": "BADFORMAT"},
                "buyer": {"name": "B"},
                "header": {"invoice_number": "X-001"},
                "line_items": [{"net_amount": 100, "vat_rate": 27, "vat_amount": 27, "gross_amount": 127}],
                "totals": {"net_total": 100, "vat_total": 27, "gross_total": 127},
            }],
        })
        warnings = result["files"][0]["validation"]["warnings"]
        assert any("adoszam" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_no_line_items(self):
        from skills.invoice_processor.workflows.process import validate_invoice

        result = await validate_invoice({
            "files": [{
                "vendor": {"name": "V"}, "buyer": {"name": "B"},
                "header": {"invoice_number": "X-001"},
                "line_items": [],
                "totals": {},
            }],
        })
        assert result["files"][0]["validation"]["is_valid"] is False


# ── Parse Tests ─────────────────────────────────────────────────────────────


class TestParseInvoice:
    @pytest.mark.asyncio
    async def test_nonexistent_path_raises(self):
        from skills.invoice_processor.workflows.process import parse_invoice

        with pytest.raises(FileNotFoundError):
            await parse_invoice({"source_path": "/nonexistent/path"})

    @pytest.mark.asyncio
    async def test_empty_directory_raises(self, tmp_path):
        from skills.invoice_processor.workflows.process import parse_invoice

        with pytest.raises(ValueError, match="No supported"):
            await parse_invoice({"source_path": str(tmp_path)})

    @pytest.mark.asyncio
    async def test_parse_txt_file(self, tmp_path):
        """Test that non-PDF files are skipped (only supported extensions)."""
        from skills.invoice_processor.workflows.process import parse_invoice

        (tmp_path / "test.csv").write_text("a,b,c", encoding="utf-8")
        with pytest.raises(ValueError, match="No supported"):
            await parse_invoice({"source_path": str(tmp_path)})


# ── Export Tests ─────────────────────────────────────────────────────────────


class TestExportInvoice:
    @pytest.mark.asyncio
    async def test_export_json(self, tmp_path):
        from skills.invoice_processor.workflows.process import export_invoice

        result = await export_invoice({
            "files": [{
                "filename": "test.pdf", "path": "/test.pdf", "direction": "incoming",
                "vendor": {"name": "Vendor"}, "buyer": {"name": "Buyer"},
                "header": {"invoice_number": "INV-1", "invoice_date": "2021-01-01",
                           "due_date": "2021-02-01", "currency": "HUF",
                           "payment_method": "atutalas", "invoice_type": "szamla",
                           "fulfillment_date": "2021-01-01", "language": "hu"},
                "line_items": [{"line_number": 1, "description": "Item",
                                "quantity": 1, "unit": "db", "unit_price": 1000,
                                "net_amount": 1000, "vat_rate": 27,
                                "vat_amount": 270, "gross_amount": 1270}],
                "totals": {"net_total": 1000, "vat_total": 270, "gross_total": 1270,
                           "vat_summary": [], "rounding_amount": 0},
                "validation": {"is_valid": True, "errors": [], "warnings": [],
                               "line_items_sum_matches": True, "vat_calculation_correct": True,
                               "tax_number_format_valid": True, "confidence_score": 1.0},
                "tables": [], "parser_used": "docling",
            }],
            "output_dir": str(tmp_path),
            "format": "json",
        })

        assert len(result["exported_files"]) == 1
        json_file = Path(result["exported_files"][0])
        assert json_file.exists()
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["header"]["invoice_number"] == "INV-1"

    @pytest.mark.asyncio
    async def test_export_csv(self, tmp_path):
        from skills.invoice_processor.workflows.process import export_invoice

        result = await export_invoice({
            "files": [{
                "filename": "test.pdf", "path": "/test.pdf", "direction": "incoming",
                "vendor": {"name": "V"}, "buyer": {"name": "B"},
                "header": {"invoice_number": "X", "invoice_date": "", "due_date": "",
                           "currency": "HUF", "payment_method": "",
                           "invoice_type": "szamla", "fulfillment_date": "", "language": "hu"},
                "line_items": [{"line_number": 1, "description": "Tetel",
                                "quantity": 2, "unit": "db", "unit_price": 500,
                                "net_amount": 1000, "vat_rate": 27,
                                "vat_amount": 270, "gross_amount": 1270}],
                "totals": {"net_total": 1000, "vat_total": 270, "gross_total": 1270,
                           "vat_summary": [], "rounding_amount": 0},
                "validation": {"is_valid": True, "errors": [], "warnings": [],
                               "line_items_sum_matches": True, "vat_calculation_correct": True,
                               "tax_number_format_valid": True, "confidence_score": 1.0},
                "tables": [], "parser_used": "docling",
            }],
            "output_dir": str(tmp_path),
            "format": "csv",
        })

        csv_path = Path(result["exported_files"][0])
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8-sig")
        assert "Tetel" in content
        assert result["export_summary"]["total_invoices"] == 1
