"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.document_adapter
    covers: [src/aiflow/pipeline/adapters/document_adapter.py]
    phase: B3
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, adapter, document, invoice-finder, acquire]
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.pipeline.adapters.document_adapter import (
    AcquireFromEmailInput,
    DocumentAcquireAdapter,
    _compute_quality_score,
)


@pytest.fixture()
def mock_ctx() -> MagicMock:
    return MagicMock()


def _make_extract_result(
    raw_text: str = "Invoice text",
    tables: list[dict[str, Any]] | None = None,
    page_count: int = 1,
    parser_used: str = "docling",
) -> SimpleNamespace:
    return SimpleNamespace(
        raw_text=raw_text,
        tables=tables or [],
        page_count=page_count,
        parser_used=parser_used,
    )


class TestAcquireWithAttachment:
    """acquire_from_email: PDF attachment → parsed document."""

    @pytest.mark.asyncio()
    async def test_pdf_attachment_returns_attachment_source(self, mock_ctx: MagicMock) -> None:
        """Email with PDF attachment returns result with source='attachment'."""
        adapter = DocumentAcquireAdapter(service=AsyncMock())
        result = await adapter._run(
            AcquireFromEmailInput(
                email_id="msg-1",
                attachments=["szamla_001.pdf"],
                has_attachment=True,
                body_snippet="Please find the invoice attached.",
            ),
            {},
            mock_ctx,
        )
        assert result["source"] == "attachment"
        assert result["file_name"] == "szamla_001.pdf"
        assert result["email_id"] == "msg-1"

    @pytest.mark.asyncio()
    async def test_non_pdf_attachment_falls_through(self, mock_ctx: MagicMock) -> None:
        """Email with non-PDF attachment (e.g. .docx) falls through to URL check."""
        adapter = DocumentAcquireAdapter(service=AsyncMock())
        result = await adapter._run(
            AcquireFromEmailInput(
                email_id="msg-2",
                attachments=["notes.docx"],
                has_attachment=True,
                body_snippet="No URLs here either.",
            ),
            {},
            mock_ctx,
        )
        # Falls through all strategies → empty source
        assert result["source"] == ""
        assert result["parser_used"] == "none"


class TestAcquireWithoutAttachment:
    """acquire_from_email: no attachment → URL fallback or skip."""

    @pytest.mark.asyncio()
    async def test_url_in_body_returns_url_source(self, mock_ctx: MagicMock) -> None:
        """Email body containing PDF URL falls back to URL source."""
        adapter = DocumentAcquireAdapter(service=AsyncMock())
        result = await adapter._run(
            AcquireFromEmailInput(
                email_id="msg-3",
                has_attachment=False,
                body_snippet="Download your invoice at https://example.com/invoices/2026_001.pdf",
            ),
            {},
            mock_ctx,
        )
        assert result["source"] == "url"
        assert result["file_name"] == "2026_001.pdf"

    @pytest.mark.asyncio()
    async def test_no_attachment_no_url_skips(self, mock_ctx: MagicMock) -> None:
        """Email with no attachment and no PDF URL → graceful skip."""
        adapter = DocumentAcquireAdapter(service=AsyncMock())
        result = await adapter._run(
            AcquireFromEmailInput(
                email_id="msg-4",
                has_attachment=False,
                body_snippet="This is just a regular email.",
            ),
            {},
            mock_ctx,
        )
        assert result["source"] == ""
        assert result["parser_used"] == "none"
        assert result["raw_text"] == ""


class TestAcquireQualityCheck:
    """acquire_from_email: quality score computation."""

    def test_long_text_with_tables_scores_high(self) -> None:
        """Document with 1000+ chars and tables gets quality >= 0.7."""
        score = _compute_quality_score(
            raw_text="A" * 1200 + " 150,000 Ft",
            tables=[{"header": ["Desc", "Qty"], "rows": [["Item", "1"]]}],
            page_count=2,
        )
        assert score >= 0.7

    def test_empty_text_scores_zero(self) -> None:
        """Empty document text produces quality score of 0."""
        score = _compute_quality_score(raw_text="", tables=[], page_count=0)
        assert score == 0.0

    def test_short_text_scores_low(self) -> None:
        """Short text (< 200 chars) without tables scores low."""
        score = _compute_quality_score(raw_text="Short text", tables=[], page_count=1)
        assert 0.0 < score < 0.5


class TestAcquireParserSelection:
    """acquire_from_email: parser selection via file path strategy."""

    @pytest.mark.asyncio()
    async def test_file_path_triggers_service_extract(self, mock_ctx: MagicMock) -> None:
        """When file_path is provided, service.extract() is called directly."""
        mock_svc = AsyncMock()
        mock_svc.extract = AsyncMock(
            return_value=_make_extract_result(
                raw_text="Invoice #2026-001\nVendor: Test Kft\nAmount: 150,000 Ft",
                tables=[{"rows": [["item", "100"]]}],
                page_count=2,
                parser_used="docling",
            )
        )
        adapter = DocumentAcquireAdapter(service=mock_svc)
        result = await adapter._run(
            AcquireFromEmailInput(email_id="msg-5", file_path="/tmp/test.pdf"),
            {},
            mock_ctx,
        )
        mock_svc.extract.assert_called_once_with(file_path="/tmp/test.pdf")
        assert result["parser_used"] == "docling"
        assert result["source"] == "attachment"
        assert result["quality_score"] > 0.0


class TestAcquireErrorHandling:
    """acquire_from_email: graceful error handling."""

    @pytest.mark.asyncio()
    async def test_service_error_returns_failed_result(self, mock_ctx: MagicMock) -> None:
        """When service.extract() raises an exception, adapter returns graceful failure."""
        mock_svc = AsyncMock()
        mock_svc.extract = AsyncMock(side_effect=RuntimeError("Parser crashed"))
        adapter = DocumentAcquireAdapter(service=mock_svc)
        result = await adapter._run(
            AcquireFromEmailInput(email_id="msg-6", file_path="/tmp/broken.pdf"),
            {},
            mock_ctx,
        )
        assert result["parser_used"] == "failed"
        assert result["quality_score"] == 0.0
        assert result["email_id"] == "msg-6"
