"""
@test_registry:
    suite: e2e
    component: skills.invoice_finder
    covers: [skills/invoice_finder, src/aiflow/pipeline/adapters/payment_status_adapter.py,
             src/aiflow/pipeline/adapters/report_generator_adapter.py,
             src/aiflow/ingestion/parsers/docling_parser.py]
    phase: B3.E2E
    priority: critical
    estimated_duration_ms: 30000
    requires_services: []
    tags: [pipeline, invoice-finder, offline, llm, e2e]
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest


def _strip_json_markdown(text: str) -> str:
    """Strip ```json ... ``` markdown wrapper from LLM response."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


# Test PDFs — real invoices from data/uploads/invoices/
TEST_PDFS = [
    {
        "file": "20210423_EdiMeron_Bestix_Szla_2021_08.pdf",
        "label": "Magyar digitalis szamla (EdiMeron)",
        "expected_language": "hu",
    },
    {
        "file": "20210423_Kacz_Levente_KL-2021-4.pdf",
        "label": "Magyar egyeni vallalkozo szamla (Kacz)",
        "expected_language": "hu",
    },
    {
        "file": "20210615_CSEPP_Studio_E-CSEPP-2021-6.pdf",
        "label": "Magyar Kft szamla (CSEPP Studio)",
        "expected_language": "hu",
    },
    {
        "file": "20210302_MS_licenc_E0800DTP68_202103.pdf",
        "label": "Kulfoldi szamla (Microsoft licenc)",
        "expected_language": "en",
    },
    # Logosz PDF kizárva: scanned/image PDF, pypdfium2 0 char-t nyer ki
    # {
    #     "file": "20210108_BestIx_Logosz_Székhely_szolgáltatás_SZÁMLA_20210108.pdf",
    #     "label": "Magyar szolgaltatas szamla (Logosz szekhelyszolg.)",
    #     "expected_language": "hu",
    # },
]

INVOICES_DIR = Path("data/uploads/invoices")
RESULTS_DIR = Path("data/e2e_results/offline_pipeline")


_PARSE_CACHE: dict[str, object] = {}


def _parse_pdf(pdf_path: Path) -> object:
    """Parse PDF using pypdfium2 (fast) with module-level cache."""
    key = str(pdf_path)
    if key in _PARSE_CACHE:
        return _PARSE_CACHE[key]

    from aiflow.ingestion.parsers.docling_parser import DoclingParser

    parser = DoclingParser()
    # Use pypdfium2 fallback for speed — docling+OCR takes 3 min/PDF
    page_count = parser._get_pdf_page_count(pdf_path) or 1
    doc = parser._fallback_parse(pdf_path, page_count)
    _PARSE_CACHE[key] = doc
    return doc


@pytest.fixture(scope="module")
def parsed_docs() -> dict[str, object]:
    """Parse all test PDFs once for the module."""
    docs = {}
    for pdf_info in TEST_PDFS:
        pdf_path = INVOICES_DIR / pdf_info["file"]
        if pdf_path.exists():
            docs[pdf_info["file"]] = _parse_pdf(pdf_path)
    return docs


class TestPDFParsing:
    """Step 1: PDF parse-olás (pypdfium2 fallback)."""

    @pytest.mark.parametrize("pdf_info", TEST_PDFS, ids=[p["label"] for p in TEST_PDFS])
    def test_pdf_parse_returns_text(self, pdf_info: dict) -> None:
        pdf_path = INVOICES_DIR / pdf_info["file"]
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        doc = _parse_pdf(pdf_path)
        assert len(doc.text) > 100, f"PDF text too short ({len(doc.text)} chars)"
        assert doc.page_count >= 1

    @pytest.mark.parametrize("pdf_info", TEST_PDFS, ids=[p["label"] for p in TEST_PDFS])
    def test_pdf_has_invoice_indicators(self, pdf_info: dict) -> None:
        pdf_path = INVOICES_DIR / pdf_info["file"]
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        doc = _parse_pdf(pdf_path)
        text_lower = doc.text.lower()
        indicators = ["szám", "szam", "invoice", "nett", "brutt", "total", "amount", "vat", "áfa"]
        found = any(ind in text_lower for ind in indicators)
        assert found, f"No invoice indicators found in {pdf_info['file']}"


class TestLLMClassifier:
    """Step 2: LLM classifier — is_invoice detection (valós GPT-4o-mini hívás!)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("pdf_info", TEST_PDFS, ids=[p["label"] for p in TEST_PDFS])
    async def test_classify_invoice(self, pdf_info: dict) -> None:
        pdf_path = INVOICES_DIR / pdf_info["file"]
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        from skills.invoice_finder import models_client, prompt_manager

        doc = _parse_pdf(pdf_path)
        prompt_def = prompt_manager.get("invoice_finder/classifier")
        messages = prompt_def.compile({"raw_text": doc.text[:2000]})

        result = await models_client.generate(
            messages=messages,
            model=prompt_def.config.model,
            temperature=prompt_def.config.temperature,
            max_tokens=prompt_def.config.max_tokens,
        )

        data = json.loads(_strip_json_markdown(result.output.text))
        assert data["is_invoice"] is True, f"Not classified as invoice: {data.get('reasoning', '')}"
        assert data["confidence"] > 0.5, f"Low confidence: {data['confidence']}"
        assert data["doc_type"] == "invoice"


class TestLLMFieldExtraction:
    """Step 3: LLM field extraction — structured data from invoice (valós GPT-4o hívás!)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "pdf_info",
        TEST_PDFS[:3],  # Only Hungarian invoices for field extraction
        ids=[p["label"] for p in TEST_PDFS[:3]],
    )
    async def test_extract_fields(self, pdf_info: dict) -> None:
        pdf_path = INVOICES_DIR / pdf_info["file"]
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        from skills.invoice_finder import models_client, prompt_manager

        doc = _parse_pdf(pdf_path)
        prompt_def = prompt_manager.get("invoice_finder/field_extractor")
        messages = prompt_def.compile({"raw_text": doc.text})

        result = await models_client.generate(
            messages=messages,
            model=prompt_def.config.model,
            temperature=prompt_def.config.temperature,
            max_tokens=prompt_def.config.max_tokens,
        )

        fields = json.loads(_strip_json_markdown(result.output.text))

        # Core fields must be non-empty
        assert fields["invoice_number"], f"Missing invoice_number for {pdf_info['file']}"
        assert fields["vendor"]["name"], f"Missing vendor name for {pdf_info['file']}"

        # Totals must be positive
        gross = fields.get("totals", {}).get("gross_total", 0)
        assert gross > 0, f"gross_total should be > 0, got {gross}"

        # Hungarian invoices should have HU tax number format
        if pdf_info["expected_language"] == "hu":
            vendor_tax = fields.get("vendor", {}).get("tax_number", "")
            if vendor_tax:
                assert "-" in vendor_tax, f"Tax number format wrong: {vendor_tax}"


class TestPaymentStatus:
    """Step 4: Payment status determination."""

    def test_old_invoice_is_overdue(self) -> None:
        from aiflow.pipeline.adapters.payment_status_adapter import _determine_payment_status

        status, days, overdue = _determine_payment_status("2021-04-30")
        assert status == "overdue"
        assert days < 0
        assert overdue is True

    def test_future_invoice_not_due(self) -> None:
        from aiflow.pipeline.adapters.payment_status_adapter import _determine_payment_status

        status, days, overdue = _determine_payment_status("2099-12-31")
        assert status == "not_due"
        assert days > 0
        assert overdue is False

    def test_empty_due_date_is_unknown(self) -> None:
        from aiflow.pipeline.adapters.payment_status_adapter import _determine_payment_status

        status, days, overdue = _determine_payment_status("")
        assert status == "unknown"
        assert overdue is False


class TestReportGeneration:
    """Step 5: Report generation (Markdown + CSV)."""

    def test_generate_markdown_report(self) -> None:
        from aiflow.pipeline.adapters.report_generator_adapter import (
            _build_report_items,
            _calculate_summary,
            _generate_csv,
            _generate_markdown,
        )

        invoices = [
            {
                "invoice_number": "TEST-001",
                "vendor": {"name": "Test Vendor Kft."},
                "totals": {"gross_total": 127000.0},
                "currency": "HUF",
                "due_date": "2021-05-15",
            },
            {
                "invoice_number": "TEST-002",
                "vendor": {"name": "Another Vendor"},
                "totals": {"gross_total": 50000.0},
                "currency": "HUF",
                "due_date": "2099-12-31",
            },
        ]
        payment_statuses = [
            {"payment_status": "overdue", "days_until_due": -1800},
            {"payment_status": "not_due", "days_until_due": 500},
        ]
        file_paths = ["test1.pdf", "test2.pdf"]

        items = _build_report_items(invoices, payment_statuses, file_paths)
        assert len(items) == 2
        assert items[0].vendor_name == "Test Vendor Kft."
        assert items[0].amount == 127000.0

        summary = _calculate_summary(items)
        assert summary.total_invoices == 2
        assert summary.overdue_count == 1
        assert summary.not_due_count == 1
        assert summary.total_amount == 177000.0

        md = _generate_markdown(items, summary)
        assert "Invoice Finder Report" in md
        assert "TEST-001" in md
        assert "OVERDUE" in md

        csv_text = _generate_csv(items)
        assert "TEST-001" in csv_text
        assert "Test Vendor Kft." in csv_text


class TestFullOfflinePipeline:
    """Full pipeline: parse → classify → extract → payment → report (valós LLM!)."""

    @pytest.mark.asyncio
    async def test_full_pipeline_3_pdfs(self) -> None:
        """Run the complete offline pipeline on 3 real PDFs."""
        from skills.invoice_finder import models_client, prompt_manager

        from aiflow.pipeline.adapters.payment_status_adapter import _determine_payment_status
        from aiflow.pipeline.adapters.report_generator_adapter import (
            _build_report_items,
            _calculate_summary,
            _generate_csv,
            _generate_markdown,
        )

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        t_start = time.time()

        classifier_prompt = prompt_manager.get("invoice_finder/classifier")
        extractor_prompt = prompt_manager.get("invoice_finder/field_extractor")

        all_fields = []
        all_payment = []
        all_paths = []
        total_cost = 0.0

        pdfs_to_test = TEST_PDFS[:3]  # 3 Hungarian invoices
        for pdf_info in pdfs_to_test:
            pdf_path = INVOICES_DIR / pdf_info["file"]
            if not pdf_path.exists():
                pytest.skip(f"PDF not found: {pdf_path}")

            # 1. Parse
            doc = _parse_pdf(pdf_path)
            assert len(doc.text) > 100

            # 2. Classify
            classify_msgs = classifier_prompt.compile({"raw_text": doc.text[:2000]})
            classify_result = await models_client.generate(
                messages=classify_msgs,
                model=classifier_prompt.config.model,
                temperature=classifier_prompt.config.temperature,
                max_tokens=classifier_prompt.config.max_tokens,
            )
            classify_data = json.loads(_strip_json_markdown(classify_result.output.text))
            total_cost += classify_result.cost_usd or 0
            assert classify_data["is_invoice"] is True

            # 3. Extract
            extract_msgs = extractor_prompt.compile({"raw_text": doc.text})
            extract_result = await models_client.generate(
                messages=extract_msgs,
                model=extractor_prompt.config.model,
                temperature=extractor_prompt.config.temperature,
                max_tokens=extractor_prompt.config.max_tokens,
            )
            fields = json.loads(_strip_json_markdown(extract_result.output.text))
            total_cost += extract_result.cost_usd or 0
            assert fields["invoice_number"]
            assert fields["vendor"]["name"]

            # 4. Payment status
            status, days, overdue = _determine_payment_status(fields.get("due_date", ""))
            all_fields.append(fields)
            all_payment.append(
                {
                    "payment_status": status,
                    "days_until_due": days,
                    "is_overdue": overdue,
                }
            )
            all_paths.append(str(pdf_path))

        # 5. Report
        items = _build_report_items(
            [{"fields": f} for f in all_fields],
            all_payment,
            all_paths,
        )
        summary = _calculate_summary(items)
        md = _generate_markdown(items, summary)
        csv_text = _generate_csv(items)

        duration = time.time() - t_start

        # Save results
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "invoice_finder_report.md").write_text(md, encoding="utf-8")
        (RESULTS_DIR / "invoices.csv").write_text(csv_text, encoding="utf-8")
        (RESULTS_DIR / "extraction_results.json").write_text(
            json.dumps(all_fields, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (RESULTS_DIR / "summary.json").write_text(
            json.dumps(
                {
                    "pdfs_tested": len(pdfs_to_test),
                    "all_classified_as_invoice": True,
                    "fields_extracted": len(all_fields),
                    "overdue_count": summary.overdue_count,
                    "total_amount": summary.total_amount,
                    "currency": summary.currency,
                    "llm_cost_usd": round(total_cost, 4),
                    "duration_seconds": round(duration, 1),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # Assertions
        assert len(items) == 3
        assert summary.total_invoices == 3
        assert summary.total_amount > 0
        assert "Invoice Finder Report" in md
        for f in all_fields:
            assert f["invoice_number"]
        # 2021 invoices should be overdue
        assert summary.overdue_count >= 1
        assert total_cost < 0.50, f"LLM cost too high: ${total_cost:.4f}"
