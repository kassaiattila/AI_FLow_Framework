"""Unit tests for BatchSourceAdapter (Phase 1b — Week 2 Day 7 — E2.2).

@test_registry: phase_1b.sources.batch_adapter

Covers metadata shape, ZIP/tar extraction, sha256/size, filename sanitization,
glob + excluded filters, zip-bomb guard, max-archive-bytes, max-file-count,
symlink/path-traversal skip, corrupt archive, empty archive, ack/reject,
fetch_next FIFO, and directory entries skipped.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import IntakePackage, IntakeSourceType
from aiflow.sources._fs import sanitize_filename
from aiflow.sources.batch_adapter import BatchSourceAdapter
from aiflow.sources.exceptions import SourceAdapterError

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def _make_adapter(
    *,
    storage_root: Path,
    tenant_id: str = "tenant_a",
    max_archive_bytes: int = 50_000_000,
    max_file_count: int = 100,
    max_compression_ratio: float = 50.0,
    glob_patterns: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
) -> BatchSourceAdapter:
    return BatchSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_archive_bytes=max_archive_bytes,
        max_file_count=max_file_count,
        max_compression_ratio=max_compression_ratio,
        glob_patterns=glob_patterns,
        excluded_patterns=excluded_patterns,
    )


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_tar_gz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_tar_with_symlink(files: dict[str, bytes], symlink_name: str, target: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        sym = tarfile.TarInfo(name=symlink_name)
        sym.type = tarfile.SYMTYPE
        sym.linkname = target
        tf.addfile(sym)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Metadata shape
# ---------------------------------------------------------------------------


def test_metadata_shape(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    meta = adapter.metadata
    assert meta.source_type == IntakeSourceType.BATCH_IMPORT
    assert meta.transport == "push"
    assert meta.requires_ack is False
    assert meta.supports_batching is True
    assert meta.name == "batch_import"
    assert BatchSourceAdapter.source_type == IntakeSourceType.BATCH_IMPORT


# ---------------------------------------------------------------------------
# 2. Single-file ZIP → 1 IntakePackage
# ---------------------------------------------------------------------------


def test_single_file_zip_yields_one_package(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    data = _make_zip({"doc.pdf": b"%PDF-1.4 test"})
    pkgs = adapter.enqueue(raw_bytes=data, filename="batch.zip")
    assert len(pkgs) == 1
    assert isinstance(pkgs[0], IntakePackage)
    assert pkgs[0].source_type == IntakeSourceType.BATCH_IMPORT
    assert pkgs[0].tenant_id == "tenant_a"
    assert len(pkgs[0].files) == 1
    assert pkgs[0].files[0].file_name == "doc.pdf"


# ---------------------------------------------------------------------------
# 3. Multi-file ZIP (3 files) → 3 IntakePackages
# ---------------------------------------------------------------------------


def test_multi_file_zip_yields_multiple_packages(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    files = {"a.txt": b"aaa", "b.txt": b"bbb", "c.txt": b"ccc"}
    data = _make_zip(files)
    pkgs = adapter.enqueue(raw_bytes=data, filename="multi.zip")
    assert len(pkgs) == 3
    names = {p.files[0].file_name for p in pkgs}
    assert names == {"a.txt", "b.txt", "c.txt"}
    # Each package has its own unique package_id.
    ids = {p.package_id for p in pkgs}
    assert len(ids) == 3


# ---------------------------------------------------------------------------
# 4. TAR.GZ unpack → correct file extraction
# ---------------------------------------------------------------------------


def test_tar_gz_extracts_correctly(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    payload = b"tar content here"
    data = _make_tar_gz({"report.csv": payload})
    pkgs = adapter.enqueue(raw_bytes=data, filename="data.tar.gz")
    assert len(pkgs) == 1
    f = pkgs[0].files[0]
    assert f.file_name == "report.csv"
    assert Path(f.file_path).read_bytes() == payload


# ---------------------------------------------------------------------------
# 5. sha256 + size_bytes correct per file
# ---------------------------------------------------------------------------


def test_sha256_and_size_bytes_correct(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    payload = b"hello batch adapter" * 10
    data = _make_zip({"payload.bin": payload})
    pkgs = adapter.enqueue(raw_bytes=data, filename="check.zip")
    f = pkgs[0].files[0]
    assert f.size_bytes == len(payload)
    assert f.sha256 == hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# 6. sanitize_filename applied to extracted names
# ---------------------------------------------------------------------------


def test_sanitize_filename_applied(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    unsafe = "weird name (draft).pdf"
    data = _make_zip({unsafe: b"x"})
    pkgs = adapter.enqueue(raw_bytes=data, filename="unsafe.zip")
    spilled = Path(pkgs[0].files[0].file_path)
    expected_safe = sanitize_filename(unsafe)
    assert spilled.name == expected_safe
    assert pkgs[0].files[0].file_name == unsafe  # original preserved


# ---------------------------------------------------------------------------
# 7. glob_patterns filter: *.pdf only extracts PDFs
# ---------------------------------------------------------------------------


def test_glob_patterns_filter(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, glob_patterns=["*.pdf"])
    data = _make_zip({"ok.pdf": b"pdf", "skip.txt": b"txt", "also.docx": b"doc"})
    pkgs = adapter.enqueue(raw_bytes=data, filename="filtered.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "ok.pdf"


# ---------------------------------------------------------------------------
# 8. excluded_patterns: *.tmp skipped inside archive
# ---------------------------------------------------------------------------


def test_excluded_patterns_filter(storage_root: Path) -> None:
    adapter = _make_adapter(
        storage_root=storage_root,
        excluded_patterns=["*.tmp"],
    )
    data = _make_zip({"good.pdf": b"x", "temp.tmp": b"y"})
    pkgs = adapter.enqueue(raw_bytes=data, filename="excl.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "good.pdf"


# ---------------------------------------------------------------------------
# 9. Zip-bomb guard: high ratio → SourceAdapterError
# ---------------------------------------------------------------------------


def test_zip_bomb_guard_rejects_high_ratio(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_compression_ratio=2.0)
    big_payload = b"\x00" * 10_000
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.bin", big_payload)
    data = buf.getvalue()
    # Compressed size << uncompressed → ratio >> 2.0.
    with pytest.raises(SourceAdapterError, match="zip-bomb guard"):
        adapter.enqueue(raw_bytes=data, filename="bomb.zip")


# ---------------------------------------------------------------------------
# 10. max_archive_bytes exceeded → SourceAdapterError
# ---------------------------------------------------------------------------


def test_max_archive_bytes_rejects_oversized(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_archive_bytes=64)
    data = _make_zip({"big.bin": b"X" * 200})
    with pytest.raises(SourceAdapterError, match="exceeds max_archive_bytes"):
        adapter.enqueue(raw_bytes=data, filename="oversized.zip")


# ---------------------------------------------------------------------------
# 11. max_file_count exceeded → SourceAdapterError
# ---------------------------------------------------------------------------


def test_max_file_count_rejects_too_many_files(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_file_count=2)
    data = _make_zip({f"f{i}.txt": b"x" for i in range(5)})
    with pytest.raises(SourceAdapterError, match="exceeds max_file_count"):
        adapter.enqueue(raw_bytes=data, filename="many.zip")


# ---------------------------------------------------------------------------
# 12. Symlink entry in tar → skipped with warning (no crash)
# ---------------------------------------------------------------------------


def test_symlink_in_tar_skipped(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    data = _make_tar_with_symlink(
        files={"real.txt": b"hello"},
        symlink_name="link.txt",
        target="/etc/passwd",
    )
    pkgs = adapter.enqueue(raw_bytes=data, filename="sym.tar.gz")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "real.txt"


# ---------------------------------------------------------------------------
# 13. Path traversal (../../etc/passwd) → skipped with warning
# ---------------------------------------------------------------------------


def test_path_traversal_in_zip_skipped(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    data = _make_zip(
        {
            "../../etc/passwd": b"root:x:0:0:",
            "safe.txt": b"ok",
        }
    )
    pkgs = adapter.enqueue(raw_bytes=data, filename="traversal.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "safe.txt"


# ---------------------------------------------------------------------------
# 14. Corrupt ZIP → SourceAdapterError
# ---------------------------------------------------------------------------


def test_corrupt_zip_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError, match="corrupt ZIP"):
        adapter.enqueue(raw_bytes=b"not a zip at all", filename="bad.zip")


# ---------------------------------------------------------------------------
# 15. Empty archive (0 files after filter) → SourceAdapterError
# ---------------------------------------------------------------------------


def test_empty_archive_after_filter_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, glob_patterns=["*.pdf"])
    data = _make_zip({"only.txt": b"text"})
    with pytest.raises(SourceAdapterError, match="no extractable files"):
        adapter.enqueue(raw_bytes=data, filename="empty_after_filter.zip")


# ---------------------------------------------------------------------------
# 16. acknowledge(unknown) → SourceAdapterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_unknown_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(uuid4())


# ---------------------------------------------------------------------------
# 17. fetch_next drains queue FIFO
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_next_drains_fifo(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    files = {"first.txt": b"1", "second.txt": b"2", "third.txt": b"3"}
    data = _make_zip(files)
    pkgs = adapter.enqueue(raw_bytes=data, filename="fifo.zip")
    assert len(pkgs) == 3

    fetched = []
    while True:
        p = await adapter.fetch_next()
        if p is None:
            break
        fetched.append(p.package_id)
    assert len(fetched) == 3
    assert fetched == [p.package_id for p in pkgs]


# ---------------------------------------------------------------------------
# 18. Directories inside archive are silently skipped
# ---------------------------------------------------------------------------


def test_directories_in_zip_skipped(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.mkdir("subdir/")
        zf.writestr("subdir/file.txt", b"nested")
    data = buf.getvalue()
    pkgs = adapter.enqueue(raw_bytes=data, filename="dirs.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "file.txt"


# ---------------------------------------------------------------------------
# 19. reject(unknown) → SourceAdapterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_unknown_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.reject(uuid4(), reason="nope")


# ---------------------------------------------------------------------------
# 20. archive_path mode reads from disk
# ---------------------------------------------------------------------------


def test_archive_path_reads_from_disk(storage_root: Path, tmp_path: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    data = _make_zip({"disk.txt": b"from disk"})
    src = tmp_path / "on_disk.zip"
    src.write_bytes(data)
    pkgs = adapter.enqueue(archive_path=src, filename="on_disk.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "disk.txt"


# ---------------------------------------------------------------------------
# 21. Unsupported format → SourceAdapterError
# ---------------------------------------------------------------------------


def test_unsupported_format_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError, match="unsupported archive format"):
        adapter.enqueue(raw_bytes=b"data", filename="file.rar")


# ---------------------------------------------------------------------------
# 22. Empty tenant_id rejected
# ---------------------------------------------------------------------------


def test_empty_tenant_id_rejected(storage_root: Path) -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        BatchSourceAdapter(storage_root=storage_root, tenant_id="")


# ---------------------------------------------------------------------------
# 23. Nested dirs in ZIP: basename extracted correctly
# ---------------------------------------------------------------------------


def test_nested_path_in_zip_uses_basename(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    data = _make_zip({"folder/subfolder/deep.txt": b"deep content"})
    pkgs = adapter.enqueue(raw_bytes=data, filename="nested.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "deep.txt"
