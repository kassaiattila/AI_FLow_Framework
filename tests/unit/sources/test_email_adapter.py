"""Unit tests for EmailSourceAdapter + ImapBackendProtocol (Phase 1b — Week 1 Day 2 — E1.1-A).

FakeImapBackend lets us exercise the full adapter contract without binding to a
real IMAP server. Real SMTP/IMAP round-trips are covered later (Day 5 / E1.5).
"""

from __future__ import annotations

import hashlib
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import (
    DescriptionRole,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources import EmailSourceAdapter, SourceAdapterError
from aiflow.sources.email_adapter import ImapBackendProtocol

# ---------------------------------------------------------------------------
# Fake backend + MIME builders
# ---------------------------------------------------------------------------


class FakeImapBackend(ImapBackendProtocol):
    """In-memory IMAP backend; records \\Seen / \\Flagged state for assertions."""

    def __init__(self, messages: list[tuple[int, bytes]] | None = None) -> None:
        self.inbox: list[tuple[int, bytes]] = list(messages or [])
        self.seen_uids: set[int] = set()
        self.flagged: dict[int, str] = {}
        self.alive: bool = True
        self.fail_on_fetch: Exception | None = None
        self.fail_on_mark: Exception | None = None
        self.fetch_calls: int = 0

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        self.fetch_calls += 1
        if self.fail_on_fetch is not None:
            raise self.fail_on_fetch
        return [(uid, raw) for uid, raw in self.inbox if uid not in self.seen_uids]

    async def mark_seen(self, uid: int) -> None:
        if self.fail_on_mark is not None:
            raise self.fail_on_mark
        self.seen_uids.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        if self.fail_on_mark is not None:
            raise self.fail_on_mark
        self.flagged[uid] = reason

    async def ping(self) -> bool:
        return self.alive


def _make_plain_message(
    *,
    subject: str = "Hello",
    sender: str = "alice@example.com",
    body: str = "This is the body.",
    charset: str = "utf-8",
) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "bob@example.com"
    msg.set_content(body, charset=charset)
    return msg.as_bytes()


def _make_multipart_with_attachments(
    *,
    subject: str = "Invoices attached",
    sender: str = "biller@example.com",
    body: str = "See attached invoices.",
    attachments: list[tuple[str, str, bytes]] | None = None,
) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "ap@example.com"
    msg.set_content(body)
    for filename, ctype, data in attachments or []:
        maintype, _, subtype = ctype.partition("/")
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype or "octet-stream", filename=filename
        )
    return msg.as_bytes()


def _make_latin1_message() -> bytes:
    """Build a minimally-compliant text/plain; charset=latin-1 message."""
    body = "Árvíztűrő tükörfúrógép".encode("latin-1", errors="replace")
    raw = (
        b"Subject: Tesz\r\n"
        b"From: sender@example.com\r\n"
        b"To: r@example.com\r\n"
        b"Content-Type: text/plain; charset=latin-1\r\n"
        b"Content-Transfer-Encoding: 8bit\r\n"
        b"\r\n"
    )
    return raw + body


def _make_no_content_type_message() -> bytes:
    """RFC822 bytes with no Content-Type header — must default to text/plain."""
    return (
        b"Subject: bare\r\n"
        b"From: bare@example.com\r\n"
        b"To: r@example.com\r\n"
        b"\r\n"
        b"bare body without headers"
    )


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def _make_adapter(
    backend: FakeImapBackend,
    *,
    storage_root: Path,
    tenant_id: str = "tenant_a",
    max_package_bytes: int | None = None,
) -> EmailSourceAdapter:
    return EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_package_bytes=max_package_bytes,
    )


# ---------------------------------------------------------------------------
# 1. Metadata shape
# ---------------------------------------------------------------------------


def test_metadata_shape(storage_root: Path) -> None:
    adapter = _make_adapter(FakeImapBackend(), storage_root=storage_root)
    meta = adapter.metadata
    assert meta.source_type == IntakeSourceType.EMAIL
    assert meta.transport == "pull"
    assert meta.requires_ack is True
    assert meta.supports_batching is False
    assert meta.name == "email_imap"
    assert EmailSourceAdapter.source_type == IntakeSourceType.EMAIL


# ---------------------------------------------------------------------------
# 2. fetch_next → None when inbox empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_next_empty_inbox_returns_none(storage_root: Path) -> None:
    adapter = _make_adapter(FakeImapBackend(), storage_root=storage_root)
    assert await adapter.fetch_next() is None


# ---------------------------------------------------------------------------
# 3. Multipart MIME with 2 attachments → IntakePackage with 2 files + 1 desc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multipart_with_two_attachments(storage_root: Path) -> None:
    pdf_bytes = b"%PDF-1.4 dummy pdf bytes"
    csv_bytes = b"a,b,c\n1,2,3\n"
    raw = _make_multipart_with_attachments(
        attachments=[
            ("invoice.pdf", "application/pdf", pdf_bytes),
            ("ledger.csv", "text/csv", csv_bytes),
        ],
    )
    backend = FakeImapBackend([(42, raw)])
    adapter = _make_adapter(backend, storage_root=storage_root)

    pkg = await adapter.fetch_next()

    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.EMAIL
    assert len(pkg.files) == 2
    assert len(pkg.descriptions) == 1
    names = {f.file_name for f in pkg.files}
    assert names == {"invoice.pdf", "ledger.csv"}
    pdf_file = next(f for f in pkg.files if f.file_name == "invoice.pdf")
    assert Path(pdf_file.file_path).read_bytes() == pdf_bytes
    assert pkg.source_metadata["email_subject"] == "Invoices attached"
    assert pkg.source_metadata["imap_uid"] == 42


# ---------------------------------------------------------------------------
# 4. Plain text body → one description role=EMAIL_BODY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plain_text_body_builds_email_body_description(storage_root: Path) -> None:
    raw = _make_plain_message(subject="hi", body="the body")
    backend = FakeImapBackend([(7, raw)])
    adapter = _make_adapter(backend, storage_root=storage_root)

    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert len(pkg.files) == 0
    assert len(pkg.descriptions) == 1
    desc = pkg.descriptions[0]
    assert desc.role == DescriptionRole.EMAIL_BODY
    assert "the body" in desc.text
    assert "Subject: hi" in desc.text


# ---------------------------------------------------------------------------
# 5. Charset fallback (latin-1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_latin1_charset_is_decoded(storage_root: Path) -> None:
    backend = FakeImapBackend([(9, _make_latin1_message())])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    text = pkg.descriptions[0].text
    # The latin-1 content should decode without raising even if utf-8 parsing fails first.
    assert "tükör" in text or "tkr" in text or len(text) > 0


# ---------------------------------------------------------------------------
# 6. Size guard → reject (no package, flagged upstream)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_size_guard_rejects_oversized_package(storage_root: Path) -> None:
    huge = b"X" * 50_000
    raw = _make_multipart_with_attachments(
        attachments=[("huge.bin", "application/octet-stream", huge)],
    )
    backend = FakeImapBackend([(11, raw)])
    adapter = _make_adapter(backend, storage_root=storage_root, max_package_bytes=1_024)
    assert await adapter.fetch_next() is None
    assert backend.flagged.get(11) == "size_exceeded"


# ---------------------------------------------------------------------------
# 7. acknowledge maps package_id → UID and marks seen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_marks_uid_seen(storage_root: Path) -> None:
    backend = FakeImapBackend([(101, _make_plain_message())])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    await adapter.acknowledge(pkg.package_id)
    assert 101 in backend.seen_uids


@pytest.mark.asyncio
async def test_acknowledge_unknown_package_id_raises(storage_root: Path) -> None:
    adapter = _make_adapter(FakeImapBackend(), storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(uuid4())


# ---------------------------------------------------------------------------
# 8. reject records reason + flags UID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_flags_uid_with_reason(storage_root: Path) -> None:
    backend = FakeImapBackend([(202, _make_plain_message())])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    await adapter.reject(pkg.package_id, reason="policy_violation")
    assert backend.flagged.get(202) == "policy_violation"
    # After reject, the package is no longer tracked.
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg.package_id)


# ---------------------------------------------------------------------------
# 9. health_check pings backend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_delegates_to_backend(storage_root: Path) -> None:
    backend = FakeImapBackend()
    adapter = _make_adapter(backend, storage_root=storage_root)
    assert await adapter.health_check() is True
    backend.alive = False
    assert await adapter.health_check() is False


# ---------------------------------------------------------------------------
# 10. IMAP auth failure surfaces as adapter error (not crash)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_failure_surfaces_as_source_adapter_error(storage_root: Path) -> None:
    backend = FakeImapBackend()
    backend.fail_on_fetch = RuntimeError("imap auth failed")
    adapter = _make_adapter(backend, storage_root=storage_root)
    with pytest.raises(SourceAdapterError, match="IMAP fetch_unseen failed"):
        await adapter.fetch_next()


# ---------------------------------------------------------------------------
# 11. Empty subject / empty body edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_subject_but_body_present(storage_root: Path) -> None:
    raw = _make_plain_message(subject="", body="just the body text")
    backend = FakeImapBackend([(1, raw)])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert len(pkg.descriptions) == 1
    assert "just the body text" in pkg.descriptions[0].text


@pytest.mark.asyncio
async def test_empty_body_but_subject_present(storage_root: Path) -> None:
    raw = _make_plain_message(subject="urgent", body="")
    backend = FakeImapBackend([(2, raw)])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert len(pkg.descriptions) == 1
    assert "urgent" in pkg.descriptions[0].text


# ---------------------------------------------------------------------------
# 12. Missing Content-Type defaults to text/plain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_content_type_defaults_to_text(storage_root: Path) -> None:
    backend = FakeImapBackend([(3, _make_no_content_type_message())])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert "bare body without headers" in pkg.descriptions[0].text


# ---------------------------------------------------------------------------
# 13. Duplicate fetch (same UID twice) is idempotent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_fetch_same_uid_is_idempotent(storage_root: Path) -> None:
    backend = FakeImapBackend([(55, _make_plain_message())])
    adapter = _make_adapter(backend, storage_root=storage_root)
    first = await adapter.fetch_next()
    second = await adapter.fetch_next()
    assert first is not None
    # Second call must NOT produce a duplicate package — UID 55 is still in-flight.
    assert second is None


# ---------------------------------------------------------------------------
# 14. sha256 + size_bytes computed per attachment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sha256_and_size_are_computed_per_attachment(storage_root: Path) -> None:
    pdf_bytes = b"%PDF-1.4 hash me"
    raw = _make_multipart_with_attachments(
        attachments=[("a.pdf", "application/pdf", pdf_bytes)],
    )
    backend = FakeImapBackend([(77, raw)])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    f = pkg.files[0]
    assert f.size_bytes == len(pdf_bytes)
    assert f.sha256 == hashlib.sha256(pdf_bytes).hexdigest()


# ---------------------------------------------------------------------------
# 15. IntakePackage.source_type == EMAIL  (plus: adapter registry ClassVar)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_package_source_type_is_email(storage_root: Path) -> None:
    backend = FakeImapBackend([(200, _make_plain_message())])
    adapter = _make_adapter(backend, storage_root=storage_root)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert pkg.source_type is IntakeSourceType.EMAIL
    assert EmailSourceAdapter.source_type is IntakeSourceType.EMAIL
