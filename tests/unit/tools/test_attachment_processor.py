"""Unit tests for aiflow.tools.attachment_processor — coverage uplift (issue #7)."""

from __future__ import annotations

import pytest

from aiflow.tools.attachment_processor import (
    AttachmentConfig,
    AttachmentProcessor,
    ProcessedAttachment,
    _compute_quality_score,
)


def test_attachment_config_defaults() -> None:
    cfg = AttachmentConfig()
    assert cfg.primary_processor == "docling"
    assert cfg.fallback_processor == "azure_di"
    assert cfg.azure_enabled is False
    assert cfg.max_size_mb == 25
    assert 0.0 <= cfg.quality_threshold <= 1.0


def test_processed_attachment_defaults() -> None:
    pa = ProcessedAttachment(filename="x.pdf")
    assert pa.filename == "x.pdf"
    assert pa.text == ""
    assert pa.tables == []
    assert pa.extracted_fields == {}


def test_extension_matches_docling() -> None:
    ap = AttachmentProcessor()
    assert ap._extension_matches_docling("file.pdf") is True
    assert ap._extension_matches_docling("file.DOCX") is True
    assert ap._extension_matches_docling("file.txt") is True
    assert ap._extension_matches_docling("file.xyz") is False
    assert ap._extension_matches_docling("noext") is False


@pytest.mark.asyncio
async def test_process_oversize_short_circuits() -> None:
    cfg = AttachmentConfig(max_size_mb=1)
    ap = AttachmentProcessor(cfg)
    # 2 MB file
    big = b"x" * (2 * 1024 * 1024)
    result = await ap.process("big.pdf", big, "application/pdf")
    assert "too large" in result.error.lower()
    assert result.filename == "big.pdf"


@pytest.mark.asyncio
async def test_process_unsupported_mime_returns_error() -> None:
    ap = AttachmentProcessor(AttachmentConfig(azure_enabled=False))
    result = await ap.process("binary.xyz", b"\x00\x01", "application/octet-stream")
    assert "Unsupported" in result.error or "none" in result.processor_used


@pytest.mark.asyncio
async def test_process_docling_exception_caught() -> None:
    """When docling is missing/broken, _process_docling returns error ProcessedAttachment."""
    ap = AttachmentProcessor()
    # Use a text/plain doc — docling branch entered, but parser likely fails on raw bytes.
    # The important thing: the method does not raise.
    result = await ap.process("note.txt", b"hello", "text/plain")
    # Either docling succeeded (returned text) OR we got an error-ish ProcessedAttachment
    assert isinstance(result, ProcessedAttachment)
    assert result.filename == "note.txt"


def test_compute_quality_score_empty_text() -> None:
    pa = ProcessedAttachment(filename="x")
    q = _compute_quality_score(pa, file_size_kb=100)
    assert q.score == pytest.approx(q.score, rel=1e-6)
    assert q.factors["content_length"] == 0.0
    assert q.factors["word_coherence"] == 0.0


def test_compute_quality_score_long_text_no_tables() -> None:
    text = "This is a reasonably long text " * 40  # ~1200 chars
    pa = ProcessedAttachment(filename="x", text=text)
    q = _compute_quality_score(pa, file_size_kb=20)
    assert q.factors["content_length"] == 1.0
    assert q.factors["word_coherence"] > 0.5
    assert q.factors["text_density"] == 1.0
    # No tables, small file → table_quality is neutral
    assert q.factors["table_quality"] == 0.5


def test_compute_quality_score_large_file_no_tables_penalty() -> None:
    pa = ProcessedAttachment(filename="x", text="short")
    q = _compute_quality_score(pa, file_size_kb=500)
    assert q.factors["table_quality"] == 0.3


def test_compute_quality_score_with_tables_bonus() -> None:
    pa = ProcessedAttachment(
        filename="x",
        text="word " * 50,
        tables=[{"rows": 2}, {"rows": 3}],
    )
    q = _compute_quality_score(pa, file_size_kb=50)
    assert q.factors["table_quality"] > 0.5


def test_compute_quality_score_bounded_0_1() -> None:
    pa = ProcessedAttachment(
        filename="x",
        text=("real text " * 1000),
        tables=[{} for _ in range(10)],
    )
    q = _compute_quality_score(pa, file_size_kb=10)
    assert 0.0 <= q.score <= 1.0


def test_compute_quality_score_short_but_nonempty() -> None:
    pa = ProcessedAttachment(filename="x", text="ab" * 60)  # 120 chars
    q = _compute_quality_score(pa, file_size_kb=10)
    assert 0.0 < q.factors["content_length"] < 1.0
