"""Unit tests for aiflow.tools.email_parser — coverage uplift (issue #7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.tools.email_parser import EmailAttachment, EmailParser, ParsedEmail

SIMPLE_EML = b"""\
From: alice@example.com
To: bob@example.com, carol@example.com
Cc: dave@example.com
Subject: Test subject
Date: Mon, 1 Jan 2024 00:00:00 +0000
Message-ID: <msg-1@example.com>
In-Reply-To: <prev@example.com>
References: <ref1@example.com> <ref2@example.com>
Content-Type: text/plain; charset=utf-8

Hello world.
"""


MULTIPART_EML = b"""\
From: sender@example.com
To: rcpt@example.com
Subject: With attachment
Message-ID: <multi-1@example.com>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUND"

--BOUND
Content-Type: text/plain; charset=utf-8

Body text here.

--BOUND
Content-Type: text/html; charset=utf-8

<p>Body <b>html</b></p>

--BOUND
Content-Type: application/pdf; name="report.pdf"
Content-Disposition: attachment; filename="report.pdf"
Content-Transfer-Encoding: base64

aGVsbG8gYXR0YWNobWVudA==

--BOUND--
"""


HTML_ONLY_EML = b"""\
From: html@example.com
Subject: HTML only
Content-Type: text/html; charset=utf-8

<p>only html</p>
"""


def test_parsed_email_defaults() -> None:
    pe = ParsedEmail()
    assert pe.message_id == ""
    assert pe.to == []
    assert pe.attachments == []


def test_email_attachment_model() -> None:
    att = EmailAttachment(
        filename="f.pdf", mime_type="application/pdf", size_bytes=3, content=b"abc"
    )
    assert att.filename == "f.pdf"
    assert att.size_bytes == 3


def test_parse_text_helper() -> None:
    parser = EmailParser()
    pe = parser.parse_text(subject="s", body="b", sender="a@example.com")
    assert pe.subject == "s"
    assert pe.body_text == "b"
    assert pe.from_ == "a@example.com"


def test_parse_eml_bytes() -> None:
    parser = EmailParser()
    pe = parser.parse_eml(SIMPLE_EML)
    assert pe.subject == "Test subject"
    assert "alice" in pe.from_
    assert any("bob" in r for r in pe.to)
    assert any("carol" in r for r in pe.to)
    assert any("dave" in r for r in pe.cc)
    assert pe.message_id == "<msg-1@example.com>"
    assert pe.in_reply_to == "<prev@example.com>"
    assert pe.references == ["<ref1@example.com>", "<ref2@example.com>"]
    assert pe.thread_id == "<prev@example.com>"  # in_reply_to wins
    assert "Hello world" in pe.body_text


def test_parse_eml_string_path() -> None:
    """Raw-string (non-filepath) is routed through message_from_string."""
    parser = EmailParser()
    raw = SIMPLE_EML.decode("utf-8")
    pe = parser.parse_eml(raw)
    assert pe.subject == "Test subject"
    assert "Hello world" in pe.body_text


def test_parse_eml_from_path(tmp_path: Path) -> None:
    parser = EmailParser()
    eml_path = tmp_path / "x.eml"
    eml_path.write_bytes(SIMPLE_EML)
    pe = parser.parse_eml(str(eml_path))
    assert pe.subject == "Test subject"


def test_parse_eml_multipart_attachment() -> None:
    parser = EmailParser()
    pe = parser.parse_eml(MULTIPART_EML)
    assert pe.subject == "With attachment"
    assert "Body text here" in pe.body_text
    assert "html" in pe.body_html.lower()
    assert len(pe.attachments) == 1
    assert pe.attachments[0].filename == "report.pdf"
    assert pe.attachments[0].mime_type == "application/pdf"
    # Content decoded from base64
    assert pe.attachments[0].content == b"hello attachment"


def test_parse_eml_html_only_fallback_to_text() -> None:
    parser = EmailParser()
    pe = parser.parse_eml(HTML_ONLY_EML)
    # No plain text → derived from HTML stripping
    assert pe.body_text != ""
    assert "only html" in pe.body_text


def test_parse_eml_thread_id_fallbacks() -> None:
    """thread_id falls back to first reference, then message_id."""
    parser = EmailParser()
    eml = b"""\
From: a@example.com
Subject: s
Message-ID: <own@example.com>
References: <first-ref@example.com>
Content-Type: text/plain

body
"""
    pe = parser.parse_eml(eml)
    assert pe.in_reply_to == ""
    assert pe.thread_id == "<first-ref@example.com>"


def test_parse_eml_thread_id_falls_back_to_message_id() -> None:
    parser = EmailParser()
    eml = b"""\
From: a@example.com
Subject: s
Message-ID: <own@example.com>
Content-Type: text/plain

body
"""
    pe = parser.parse_eml(eml)
    assert pe.thread_id == "<own@example.com>"


def test_parse_eml_invalid_type_raises() -> None:
    parser = EmailParser()
    with pytest.raises(ValueError):
        parser.parse_eml(42)  # type: ignore[arg-type]
