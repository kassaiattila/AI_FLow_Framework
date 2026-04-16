"""Unit tests for FileSourceAdapter (Phase 1b — Week 1 Day 4 — E1.3).

@test_registry: phase_1b.sources.file_adapter

Covers metadata shape, enqueue() input validation, MIME detection,
sha256/size computation, filename sanitization, size guard, queue draining,
ack/reject bookkeeping, optional description kwarg, and health_check.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import (
    DescriptionRole,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources import FileSourceAdapter, SourceAdapterError


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def _make_adapter(
    *,
    storage_root: Path,
    tenant_id: str = "tenant_a",
    max_package_bytes: int | None = None,
    mime_detect=None,
) -> FileSourceAdapter:
    return FileSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_package_bytes=max_package_bytes,
        mime_detect=mime_detect,
    )


# ---------------------------------------------------------------------------
# 1. Metadata shape
# ---------------------------------------------------------------------------


def test_metadata_shape(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    meta = adapter.metadata
    assert meta.source_type == IntakeSourceType.FILE_UPLOAD
    assert meta.transport == "push"
    assert meta.requires_ack is False
    assert meta.supports_batching is False
    assert meta.name == "file_upload"
    assert FileSourceAdapter.source_type == IntakeSourceType.FILE_UPLOAD


# ---------------------------------------------------------------------------
# 2. enqueue(raw_bytes=...) builds IntakePackage with 1 IntakeFile
# ---------------------------------------------------------------------------


def test_enqueue_raw_bytes_builds_single_file_package(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    payload = b"%PDF-1.4 dummy"
    pkg = adapter.enqueue(raw_bytes=payload, filename="doc.pdf")

    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.FILE_UPLOAD
    assert pkg.tenant_id == "tenant_a"
    assert len(pkg.files) == 1
    assert len(pkg.descriptions) == 0

    f = pkg.files[0]
    assert f.file_name == "doc.pdf"
    assert f.size_bytes == len(payload)
    assert f.sha256 == hashlib.sha256(payload).hexdigest()
    assert Path(f.file_path).read_bytes() == payload


# ---------------------------------------------------------------------------
# 3. enqueue(file_path=...) reads from disk
# ---------------------------------------------------------------------------


def test_enqueue_file_path_reads_from_disk(storage_root: Path, tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    src.write_bytes(b"hello from disk")
    adapter = _make_adapter(storage_root=storage_root)

    pkg = adapter.enqueue(file_path=src, filename="source.txt")
    assert len(pkg.files) == 1
    spilled = Path(pkg.files[0].file_path)
    # Spilled to storage_root (not the original path).
    assert spilled != src
    assert spilled.read_bytes() == b"hello from disk"


# ---------------------------------------------------------------------------
# 4. Missing both raw_bytes AND file_path → ValueError
# ---------------------------------------------------------------------------


def test_enqueue_without_raw_bytes_or_file_path_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(ValueError, match="exactly one of file_path or raw_bytes"):
        adapter.enqueue(filename="x.pdf")


# ---------------------------------------------------------------------------
# 5. Both raw_bytes AND file_path → ValueError (ambiguous)
# ---------------------------------------------------------------------------


def test_enqueue_with_both_inputs_raises(storage_root: Path, tmp_path: Path) -> None:
    src = tmp_path / "src.bin"
    src.write_bytes(b"bytes")
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(ValueError, match="exactly one of file_path or raw_bytes"):
        adapter.enqueue(file_path=src, raw_bytes=b"other", filename="src.bin")


# ---------------------------------------------------------------------------
# 6. MIME detection defaults via stdlib mimetypes
# ---------------------------------------------------------------------------


def test_mime_detect_default_recognises_pdf_extension(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="x.pdf")
    assert pkg.files[0].mime_type == "application/pdf"


# ---------------------------------------------------------------------------
# 7. Unknown extension falls back to application/octet-stream
# ---------------------------------------------------------------------------


def test_unknown_extension_falls_back_to_octet_stream(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="weirdfile.zzznope")
    assert pkg.files[0].mime_type == "application/octet-stream"


# ---------------------------------------------------------------------------
# 8. DI mime_detect override is honored
# ---------------------------------------------------------------------------


def test_mime_detect_override_is_honored(storage_root: Path) -> None:
    def _detect(_payload: bytes, _filename: str) -> str:
        return "application/x-custom"

    adapter = _make_adapter(storage_root=storage_root, mime_detect=_detect)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="file.pdf")
    assert pkg.files[0].mime_type == "application/x-custom"


# ---------------------------------------------------------------------------
# 9. Explicit mime_type kwarg wins over detection
# ---------------------------------------------------------------------------


def test_explicit_mime_type_kwarg_wins(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="x.pdf", mime_type="image/png")
    assert pkg.files[0].mime_type == "image/png"


# ---------------------------------------------------------------------------
# 10. Attachment spilled under storage_root/{tenant}/{package_id}/{sanitized}
# ---------------------------------------------------------------------------


def test_attachment_spilled_under_tenant_and_package_dir(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="doc.pdf")
    dest = Path(pkg.files[0].file_path)
    expected_parent = storage_root / "tenant_a" / str(pkg.package_id)
    assert dest.parent == expected_parent
    assert dest.name == "doc.pdf"


# ---------------------------------------------------------------------------
# 11. Unsafe filename sanitized
# ---------------------------------------------------------------------------


def test_unsafe_filename_is_sanitized(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="../../etc/passwd")
    dest = Path(pkg.files[0].file_path)
    # Path on disk must stay within the package directory — no traversal possible
    # because `/` and `\` are stripped even though literal `.` / `..` substrings
    # survive (they are not path separators).
    assert dest.parent == storage_root / "tenant_a" / str(pkg.package_id)
    assert "/" not in dest.name
    assert "\\" not in dest.name
    # Original filename is preserved on the Pydantic field for audit.
    assert pkg.files[0].file_name == "../../etc/passwd"


# ---------------------------------------------------------------------------
# 12. Size guard rejects oversized upload (no package emitted)
# ---------------------------------------------------------------------------


def test_size_guard_rejects_oversized_upload(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_package_bytes=16)
    with pytest.raises(SourceAdapterError, match="exceeds max_package_bytes"):
        adapter.enqueue(raw_bytes=b"X" * 64, filename="big.bin")
    # No package queued and no directory left behind.
    # (We don't assert absence of tenant dir since size check happens before mkdir.)
    assert len(adapter._queue) == 0  # noqa: SLF001


# ---------------------------------------------------------------------------
# 13. fetch_next drains queue FIFO
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_next_drains_queue_fifo(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    p1 = adapter.enqueue(raw_bytes=b"one", filename="a.txt")
    p2 = adapter.enqueue(raw_bytes=b"two", filename="b.txt")

    first = await adapter.fetch_next()
    second = await adapter.fetch_next()
    third = await adapter.fetch_next()

    assert first is not None and first.package_id == p1.package_id
    assert second is not None and second.package_id == p2.package_id
    assert third is None


# ---------------------------------------------------------------------------
# 14. fetch_next on empty queue → None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_next_empty_queue_returns_none(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    assert await adapter.fetch_next() is None


# ---------------------------------------------------------------------------
# 15. acknowledge clears in-flight map; double-ack raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_clears_in_flight_and_double_ack_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="a.txt")
    await adapter.acknowledge(pkg.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg.package_id)


@pytest.mark.asyncio
async def test_acknowledge_unknown_package_id_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(uuid4())


# ---------------------------------------------------------------------------
# 16. reject discards package
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_discards_package(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="a.txt")
    await adapter.reject(pkg.package_id, reason="policy_violation")
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg.package_id)


# ---------------------------------------------------------------------------
# 17. description kwarg adds USER_NOTE description
# ---------------------------------------------------------------------------


def test_description_kwarg_adds_user_note_description(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="a.pdf", description="please review by friday")
    assert len(pkg.descriptions) == 1
    d = pkg.descriptions[0]
    assert d.role == DescriptionRole.USER_NOTE
    assert d.text == "please review by friday"


def test_blank_description_is_ignored(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    pkg = adapter.enqueue(raw_bytes=b"x", filename="a.pdf", description="   ")
    assert len(pkg.descriptions) == 0


# ---------------------------------------------------------------------------
# 18. health_check: writable dir → True; missing parent still created → True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_creates_and_probes_storage_root(tmp_path: Path) -> None:
    # Point at a nested path that doesn't exist yet — adapter must create it.
    storage = tmp_path / "nested" / "storage"
    adapter = FileSourceAdapter(storage_root=storage, tenant_id="t")
    assert await adapter.health_check() is True
    assert storage.is_dir()


# ---------------------------------------------------------------------------
# 19. Empty tenant_id rejected at construction
# ---------------------------------------------------------------------------


def test_empty_tenant_id_rejected(storage_root: Path) -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        FileSourceAdapter(storage_root=storage_root, tenant_id="")


# ---------------------------------------------------------------------------
# 20. Empty filename rejected
# ---------------------------------------------------------------------------


def test_empty_filename_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(ValueError, match="filename"):
        adapter.enqueue(raw_bytes=b"x", filename="")


# ---------------------------------------------------------------------------
# 21. Storage root not yet existing → adapter creates tenant + package dirs
# ---------------------------------------------------------------------------


def test_missing_storage_root_is_created_on_enqueue(tmp_path: Path) -> None:
    storage = tmp_path / "fresh"
    adapter = FileSourceAdapter(storage_root=storage, tenant_id="tenant_a")
    pkg = adapter.enqueue(raw_bytes=b"x", filename="a.txt")
    assert (storage / "tenant_a" / str(pkg.package_id) / "a.txt").is_file()
