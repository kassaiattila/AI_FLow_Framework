"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.email_adapter
    covers: [src/aiflow/pipeline/adapters/email_adapter.py]
    phase: B3
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, adapter, email, invoice-finder, search]
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.pipeline.adapters.email_adapter import (
    EmailSearchInvoicesAdapter,
    SearchInvoicesInput,
    _score_email_for_invoice,
)


def _make_email(
    message_id: str = "msg-1",
    subject: str = "",
    sender: str = "test@example.com",
    body_text: str = "",
    received_at: str = "2026-04-01",
    attachments: list[dict[str, Any]] | None = None,
) -> SimpleNamespace:
    """Create a mock email object matching EmailConnectorService output."""
    return SimpleNamespace(
        message_id=message_id,
        subject=subject,
        sender=sender,
        body_text=body_text,
        received_at=received_at,
        attachments=attachments or [],
    )


def _make_fetch_result(emails: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(emails=emails)


@pytest.fixture()
def mock_service() -> AsyncMock:
    svc = AsyncMock()
    svc.fetch_emails = AsyncMock(return_value=_make_fetch_result([]))
    return svc


@pytest.fixture()
def mock_ctx() -> MagicMock:
    return MagicMock()


class TestSearchInvoicesKeywordMatch:
    """search_invoices: keyword matching scores emails correctly."""

    def test_subject_keyword_produces_positive_score(self) -> None:
        """Email with 'szamla' in subject gets a score > 0."""
        score = _score_email_for_invoice(
            subject="Re: Szamla - 2026/001",
            body_text="",
            attachment_names=[],
        )
        assert score > 0.0

    def test_body_keyword_produces_positive_score(self) -> None:
        """Email with 'fizetendo' in body gets a score > 0."""
        score = _score_email_for_invoice(
            subject="Important document",
            body_text="A fizetendo osszeg: 150.000 Ft. Hatarido: 2026.04.15.",
            attachment_names=[],
        )
        assert score > 0.0

    def test_combined_keywords_higher_score(self) -> None:
        """Multiple keyword matches across subject + body produce higher score."""
        score_low = _score_email_for_invoice(
            subject="document",
            body_text="please review",
            attachment_names=[],
        )
        score_high = _score_email_for_invoice(
            subject="Szamla - fizetesi felszolitas",
            body_text="Fizetendo osszeg netto brutto hatarido",
            attachment_names=["szamla_2026_001.pdf"],
        )
        assert score_high > score_low


class TestSearchInvoicesNoMatch:
    """search_invoices: non-invoice emails are filtered out."""

    @pytest.mark.asyncio()
    async def test_non_invoice_email_returns_empty(
        self, mock_service: AsyncMock, mock_ctx: MagicMock
    ) -> None:
        """Emails without invoice keywords produce empty result list."""
        mock_service.fetch_emails.return_value = _make_fetch_result(
            [
                _make_email(
                    subject="Team meeting tomorrow", body_text="Let's discuss the roadmap."
                ),
                _make_email(subject="Vacation request", body_text="I'd like to take Friday off."),
            ]
        )
        adapter = EmailSearchInvoicesAdapter(service=mock_service)
        result = await adapter._run(
            SearchInvoicesInput(connector_id="cfg-1", relevance_threshold=0.3),
            {},
            mock_ctx,
        )
        assert result["total_scanned"] == 2
        assert result["total_matched"] == 0
        assert result["emails"] == []


class TestSearchInvoicesAttachmentBoost:
    """search_invoices: PDF attachments boost relevance score."""

    def test_pdf_attachment_boosts_score(self) -> None:
        """PDF attachment adds +0.15 to the score."""
        score_no_att = _score_email_for_invoice(
            subject="Szamla",
            body_text="",
            attachment_names=[],
        )
        score_with_att = _score_email_for_invoice(
            subject="Szamla",
            body_text="",
            attachment_names=["document.pdf"],
        )
        assert score_with_att > score_no_att
        assert score_with_att - score_no_att >= 0.15

    def test_invoice_named_pdf_gets_extra_boost(self) -> None:
        """PDF named 'szamla_001.pdf' gets additional +0.10 pattern bonus."""
        score_generic = _score_email_for_invoice(
            subject="",
            body_text="",
            attachment_names=["document.pdf"],
        )
        score_invoice = _score_email_for_invoice(
            subject="",
            body_text="",
            attachment_names=["szamla_2026_001.pdf"],
        )
        assert score_invoice > score_generic


class TestSearchInvoicesHungarianKeywords:
    """search_invoices: Hungarian invoice keywords are recognized."""

    def test_hungarian_subject_keywords(self) -> None:
        """Hungarian keywords like 'számla', 'fizetési' in subject score > 0."""
        score = _score_email_for_invoice(
            subject="Számla - fizetési felszólítás",
            body_text="",
            attachment_names=[],
        )
        assert score > 0.0

    def test_hungarian_body_keywords(self) -> None:
        """Hungarian body terms: összeg, nettó, bruttó, határidő produce score > 0."""
        score = _score_email_for_invoice(
            subject="",
            body_text="Az összeg nettó 100.000 Ft, bruttó 127.000 Ft. Határidő: 2026.04.30.",
            attachment_names=[],
        )
        assert score > 0.0


class TestSearchInvoicesThresholdFilter:
    """search_invoices: threshold correctly filters low-score emails."""

    @pytest.mark.asyncio()
    async def test_below_threshold_filtered_out(
        self, mock_service: AsyncMock, mock_ctx: MagicMock
    ) -> None:
        """Emails scoring below the relevance threshold are excluded from results."""
        mock_service.fetch_emails.return_value = _make_fetch_result(
            [
                # This should score high (subject + body + attachment keywords)
                _make_email(
                    message_id="invoice-email",
                    subject="Szamla 2026/001",
                    body_text="Fizetendo osszeg: 150.000 Ft",
                    attachments=[{"filename": "szamla_001.pdf", "file_path": "/tmp/szamla.pdf"}],
                ),
                # This should score ~0 (no keywords)
                _make_email(
                    message_id="normal-email",
                    subject="Weekly sync",
                    body_text="Agenda for the meeting: 1. Status update",
                ),
            ]
        )
        adapter = EmailSearchInvoicesAdapter(service=mock_service)
        result = await adapter._run(
            SearchInvoicesInput(connector_id="cfg-1", relevance_threshold=0.3),
            {},
            mock_ctx,
        )
        assert result["total_scanned"] == 2
        assert result["total_matched"] == 1
        assert result["emails"][0]["email_id"] == "invoice-email"
        assert result["emails"][0]["score"] >= 0.3
