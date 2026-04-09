"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.classifier_adapter
    covers:
      - src/aiflow/pipeline/adapters/classifier_adapter.py
      - skills/invoice_finder/prompts/invoice_classifier.yaml
    phase: B3
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [pipeline, adapter, classifier, invoice-finder]
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from aiflow.pipeline.adapters.classifier_adapter import ClassifierAdapter, ClassifyInput

PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "invoice_finder"
    / "prompts"
    / "invoice_classifier.yaml"
)

# --- Sample texts for classification ---
HUNGARIAN_INVOICE_TEXT = """
SZÁMLA / INVOICE
Számlaszám: SZ-2026/001
Kibocsátó: BestIx Kft.
Cím: 1011 Budapest, Fő utca 1.
Adószám: 12345678-2-41

Vevő: Test Customer Kft.
Cím: 1055 Budapest, Kossuth tér 5.
Adószám: 87654321-2-42

Teljesítés dátuma: 2026.03.15.
Fizetési határidő: 2026.04.15.
Fizetés módja: Átutalás

Tétel | Mennyiség | Egységár | Nettó | ÁFA 27% | Bruttó
Szoftverfejlesztés | 40 óra | 25.000 Ft | 1.000.000 Ft | 270.000 Ft | 1.270.000 Ft

Nettó összesen: 1.000.000 Ft
ÁFA összesen: 270.000 Ft
Fizetendő összesen: 1.270.000 Ft
"""

ENGLISH_INVOICE_TEXT = """
INVOICE
Invoice Number: INV-2026-0042
Date: March 15, 2026
Due Date: April 15, 2026

Bill From:
BestIx Ltd.
1011 Budapest, Fő utca 1.

Bill To:
Test Customer Ltd.
1055 Budapest, Kossuth tér 5.

Description | Qty | Unit Price | Amount
Software Development | 40 hrs | $50.00 | $2,000.00

Subtotal: $2,000.00
VAT (27%): $540.00
Total: $2,540.00

Payment Terms: Net 30
"""

NOT_INVOICE_TEXT = """
COOPERATION AGREEMENT

This agreement is entered into between BestIx Kft. (Service Provider) and
Test Customer Kft. (Client) on March 15, 2026.

1. Scope of Work
The Service Provider agrees to provide software development services
to the Client as specified in Appendix A.

2. Term
This agreement shall be effective from April 1, 2026 to March 31, 2027.

3. Confidentiality
Both parties agree to maintain strict confidentiality of all information.
"""


@pytest.fixture()
def mock_ctx() -> MagicMock:
    return MagicMock()


def _make_classify_result(
    label: str = "invoice",
    confidence: float = 0.95,
    method: str = "llm",
    all_scores: dict[str, float] | None = None,
) -> MagicMock:
    result = MagicMock()
    result.label = label
    result.confidence = confidence
    result.method = method
    result.all_scores = all_scores or {"invoice": confidence, "other": 1.0 - confidence}
    return result


class TestClassifyInvoiceDetected:
    """Classifier correctly identifies invoice documents."""

    @pytest.mark.asyncio()
    async def test_hungarian_invoice_text_classified_as_invoice(self, mock_ctx: MagicMock) -> None:
        """Hungarian invoice text → label='invoice', confidence > 0.8."""
        mock_svc = AsyncMock()
        mock_svc.classify = AsyncMock(
            return_value=_make_classify_result(label="invoice", confidence=0.95)
        )
        adapter = ClassifierAdapter(service=mock_svc)
        result = await adapter._run(
            ClassifyInput(text=HUNGARIAN_INVOICE_TEXT, subject="invoice_finder"),
            {},
            mock_ctx,
        )
        assert result["label"] == "invoice"
        assert result["confidence"] >= 0.8
        mock_svc.classify.assert_called_once()


class TestClassifyNotInvoice:
    """Classifier correctly rejects non-invoice documents."""

    @pytest.mark.asyncio()
    async def test_contract_text_not_classified_as_invoice(self, mock_ctx: MagicMock) -> None:
        """Contract text → label != 'invoice'."""
        mock_svc = AsyncMock()
        mock_svc.classify = AsyncMock(
            return_value=_make_classify_result(label="contract", confidence=0.90)
        )
        adapter = ClassifierAdapter(service=mock_svc)
        result = await adapter._run(
            ClassifyInput(text=NOT_INVOICE_TEXT, subject="invoice_finder"),
            {},
            mock_ctx,
        )
        assert result["label"] != "invoice"


class TestClassifyConfidenceThreshold:
    """Classifier confidence threshold handling."""

    @pytest.mark.asyncio()
    async def test_low_confidence_flagged(self, mock_ctx: MagicMock) -> None:
        """Document with confidence < 0.8 → needs human review."""
        mock_svc = AsyncMock()
        mock_svc.classify = AsyncMock(
            return_value=_make_classify_result(label="invoice", confidence=0.55)
        )
        adapter = ClassifierAdapter(service=mock_svc)
        result = await adapter._run(
            ClassifyInput(text="Ambiguous document text..."),
            {},
            mock_ctx,
        )
        # Low confidence means this would go to human_review queue
        assert result["confidence"] < 0.8


class TestClassifyHungarianInvoice:
    """Classifier handles Hungarian invoice terminology."""

    def test_prompt_yaml_exists_and_valid(self) -> None:
        """invoice_classifier.yaml exists and has correct structure."""
        assert PROMPT_PATH.exists(), f"Prompt not found at {PROMPT_PATH}"
        data = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
        assert data["name"] == "invoice_finder/classifier"
        assert "system" in data
        assert "user" in data
        assert "{{ raw_text }}" in data["user"]
        assert data["config"]["temperature"] == 0.0
        assert data["config"]["response_format"] == "json_object"

    def test_prompt_system_contains_hungarian_terms(self) -> None:
        """System prompt includes Hungarian invoice keywords."""
        data = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
        system = data["system"].lower()
        assert "szamla" in system or "számla" in system
        assert "áfa" in system or "vat" in system


class TestClassifyEnglishInvoice:
    """Classifier handles English invoices."""

    @pytest.mark.asyncio()
    async def test_english_invoice_classified_correctly(self, mock_ctx: MagicMock) -> None:
        """English invoice text → label='invoice', confidence > 0.8."""
        mock_svc = AsyncMock()
        mock_svc.classify = AsyncMock(
            return_value=_make_classify_result(label="invoice", confidence=0.92)
        )
        adapter = ClassifierAdapter(service=mock_svc)
        result = await adapter._run(
            ClassifyInput(text=ENGLISH_INVOICE_TEXT, subject="invoice_finder"),
            {},
            mock_ctx,
        )
        assert result["label"] == "invoice"
        assert result["confidence"] > 0.8
