"""
@test_registry:
    suite: unit
    component: aiflow.engine.confidence
    covers: [src/aiflow/engine/confidence.py]
    phase: B3.5
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [confidence, scoring, engine]
"""

from __future__ import annotations

import pytest

from aiflow.engine.confidence import (
    DEFAULT_SOURCE_QUALITY,
    DocumentConfidence,
    FieldConfidence,
    FieldConfidenceCalculator,
)


@pytest.fixture
def calculator() -> FieldConfidenceCalculator:
    return FieldConfidenceCalculator()


class TestDateFieldFormat:
    def test_iso_date_scores_high(self, calculator: FieldConfidenceCalculator) -> None:
        """ISO date 'YYYY-MM-DD' → format_match 1.0, regex 1.0."""
        fc = calculator.compute_field(
            "invoice_date", "2021-04-15", field_type="date", parser_used="docling"
        )
        assert isinstance(fc, FieldConfidence)
        assert fc.factors["format_match"] == 1.0
        assert fc.factors["regex_validation"] == 1.0
        assert fc.confidence >= 0.85

    def test_garbage_date_scores_low(self, calculator: FieldConfidenceCalculator) -> None:
        """Non-date string → format 0.3, regex 0.2."""
        fc = calculator.compute_field(
            "invoice_date", "aprilis 15", field_type="date", parser_used="docling"
        )
        assert fc.factors["format_match"] < 1.0
        assert fc.factors["regex_validation"] < 0.5
        assert fc.confidence < 0.6

    def test_empty_date_zero_format(self, calculator: FieldConfidenceCalculator) -> None:
        """Empty value → format 0, regex 0."""
        fc = calculator.compute_field("invoice_date", "", field_type="date", parser_used="docling")
        assert fc.factors["format_match"] == 0.0
        assert fc.factors["regex_validation"] == 0.0


class TestTaxNumberField:
    def test_valid_hu_tax_number(self, calculator: FieldConfidenceCalculator) -> None:
        """HU tax number format XXXXXXXX-X-XX passes regex."""
        fc = calculator.compute_field(
            "vendor_tax_number",
            "12345678-2-42",
            field_type="string",
            parser_used="docling",
        )
        assert fc.factors["regex_validation"] == 1.0
        assert fc.factors["format_match"] == 1.0
        assert fc.confidence >= 0.85

    def test_invalid_tax_number_fails_regex(self, calculator: FieldConfidenceCalculator) -> None:
        """Wrong tax number format fails regex (but has format_match=1.0 for non-empty string)."""
        fc = calculator.compute_field(
            "vendor_tax_number",
            "12345",
            field_type="string",
            parser_used="docling",
        )
        assert fc.factors["regex_validation"] == 0.2
        # format_match still 1.0 because it's a non-empty string, but
        # regex 0.2 × 0.25 pulls confidence to exactly 0.80 with docling source
        assert fc.confidence <= 0.80


class TestCrossFieldAmountConsistency:
    def test_net_vat_gross_consistent(self, calculator: FieldConfidenceCalculator) -> None:
        """net + vat ≈ gross (within 1%) → consistency 1.0."""
        fields = {
            "net_total": 100000.0,
            "vat_total": 27000.0,
            "gross_total": 127000.0,
        }
        fc = calculator.compute_field(
            "gross_total",
            127000.0,
            field_type="number",
            all_fields=fields,
            parser_used="docling",
        )
        assert fc.factors["cross_field_consistency"] == 1.0

    def test_net_vat_gross_inconsistent(self, calculator: FieldConfidenceCalculator) -> None:
        """net + vat far from gross → consistency 0.2."""
        fields = {
            "net_total": 100000.0,
            "vat_total": 27000.0,
            "gross_total": 200000.0,  # way off from 127000
        }
        fc = calculator.compute_field(
            "gross_total",
            200000.0,
            field_type="number",
            all_fields=fields,
            parser_used="docling",
        )
        assert fc.factors["cross_field_consistency"] == 0.2

    def test_missing_amount_neutral(self, calculator: FieldConfidenceCalculator) -> None:
        """Missing one of the three amounts → neutral 0.7 (can't verify)."""
        fields = {"net_total": 100000.0, "gross_total": 127000.0}  # no vat
        fc = calculator.compute_field(
            "gross_total",
            127000.0,
            field_type="number",
            all_fields=fields,
            parser_used="docling",
        )
        assert fc.factors["cross_field_consistency"] == 0.7


class TestSourceQualityFactor:
    def test_docling_high_quality(self, calculator: FieldConfidenceCalculator) -> None:
        fc = calculator.compute_field(
            "invoice_number",
            "EDI-2021-001",
            field_type="string",
            parser_used="docling",
        )
        assert fc.factors["source_quality"] == DEFAULT_SOURCE_QUALITY["docling"]

    def test_ocr_lower_quality(self, calculator: FieldConfidenceCalculator) -> None:
        fc = calculator.compute_field(
            "invoice_number",
            "EDI-2021-001",
            field_type="string",
            parser_used="ocr",
        )
        assert fc.factors["source_quality"] == DEFAULT_SOURCE_QUALITY["ocr"]

    def test_unknown_parser_falls_back(self, calculator: FieldConfidenceCalculator) -> None:
        fc = calculator.compute_field(
            "invoice_number",
            "EDI-2021-001",
            field_type="string",
            parser_used="mystery_parser",
        )
        assert fc.factors["source_quality"] == DEFAULT_SOURCE_QUALITY["unknown"]


class TestDocumentOverallConfidence:
    def test_full_valid_invoice_high_confidence(
        self, calculator: FieldConfidenceCalculator
    ) -> None:
        """Complete valid HU invoice → overall confidence close to 1.0 × source."""
        fields = {
            "invoice_number": "EDI-2021-008",
            "invoice_date": "2021-04-23",
            "due_date": "2021-05-15",
            "vendor_name": "EdiMeron Kft.",
            "vendor_tax_number": "12345678-2-42",
            "net_total": 100000.0,
            "vat_total": 27000.0,
            "gross_total": 127000.0,
        }
        field_types = {
            "invoice_number": "string",
            "invoice_date": "date",
            "due_date": "date",
            "vendor_name": "string",
            "vendor_tax_number": "string",
            "net_total": "number",
            "vat_total": "number",
            "gross_total": "number",
        }
        doc = calculator.compute_document(
            fields,
            field_types=field_types,
            mandatory_fields=[
                "invoice_number",
                "invoice_date",
                "vendor_name",
                "gross_total",
            ],
            parser_used="docling",
        )
        assert isinstance(doc, DocumentConfidence)
        assert doc.structural_penalty == 1.0  # No missing mandatory
        assert doc.source_quality == 1.0
        assert doc.overall >= 0.85
        assert len(doc.field_scores) == 8
        assert doc.missing_mandatory == []

    def test_missing_mandatory_applies_penalty(self, calculator: FieldConfidenceCalculator) -> None:
        """Each missing mandatory field subtracts 0.15 from structural_penalty."""
        fields = {
            "invoice_number": "EDI-2021-008",
            "vendor_name": "EdiMeron Kft.",
            # Missing invoice_date + gross_total (both mandatory)
        }
        doc = calculator.compute_document(
            fields,
            mandatory_fields=[
                "invoice_number",
                "invoice_date",
                "vendor_name",
                "gross_total",
            ],
            parser_used="docling",
        )
        # 2 missing × 0.15 = 0.30 penalty → structural 0.70
        assert doc.structural_penalty == pytest.approx(0.70, abs=0.001)
        assert set(doc.missing_mandatory) == {"invoice_date", "gross_total"}
        # overall must be strictly less than it would be without missing fields
        assert doc.overall < 0.8

    def test_empty_document_zero_confidence(self, calculator: FieldConfidenceCalculator) -> None:
        """No fields + 4 mandatory → overall drops hard but not below min."""
        doc = calculator.compute_document(
            {},
            mandatory_fields=["invoice_number", "invoice_date", "vendor_name", "gross_total"],
            parser_used="unknown",
        )
        assert len(doc.field_scores) == 0
        assert doc.overall == 0.0
        # 4 missing mandatory × 0.15 = 0.60 penalty, capped at _MIN_STRUCTURAL 0.30
        assert doc.structural_penalty == pytest.approx(0.40, abs=0.001)
