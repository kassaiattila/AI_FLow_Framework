"""E2E — BatchSourceAdapter (Phase 1b Week 2 Day 10 / E2.4).

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, intake, source_adapter, batch_import]

Real pipeline: BatchSourceAdapter unpacks real ZIP/tar archives into the real
tmp storage_root and emits one IntakePackage per extracted file. All payloads
are materialized on disk and re-read through ``Path.read_bytes`` to prove
there is no in-memory shortcut.

DB persistence round-trip is out of scope per feedback_asyncpg_pool_event_loop.md.
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
from aiflow.sources import BatchSourceAdapter, SourceAdapterError
from aiflow.sources.registry import SourceAdapterRegistry


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


def test_batch_source_happy_path_zip_multi_file(
    phase_1b_storage_root: Path,
    phase_1b_source_registry: SourceAdapterRegistry,
) -> None:
    """ZIP with three files → three IntakePackages, bytes round-tripped on disk."""
    tenant_id = f"tenant-e2e-batch-happy-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_happy_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(storage_root=storage_root, tenant_id=tenant_id)
    phase_1b_source_registry.register(BatchSourceAdapter)
    assert phase_1b_source_registry.has(IntakeSourceType.BATCH_IMPORT)

    files = {
        "invoice-a.pdf": b"%PDF-1.4 a",
        "invoice-b.pdf": b"%PDF-1.4 b",
        "ledger.csv": b"col_a,col_b\n1,2\n",
    }
    data = _make_zip(files)

    pkgs = adapter.enqueue(raw_bytes=data, filename="weekly-batch.zip")
    assert len(pkgs) == 3
    assert {p.source_type for p in pkgs} == {IntakeSourceType.BATCH_IMPORT}
    by_name = {p.files[0].file_name: p for p in pkgs}
    assert set(by_name) == set(files)

    for name, payload in files.items():
        pkg = by_name[name]
        on_disk = Path(pkg.files[0].file_path)
        assert on_disk.exists()
        assert on_disk.read_bytes() == payload
        assert pkg.files[0].sha256 == hashlib.sha256(payload).hexdigest()
        assert on_disk.is_relative_to(storage_root / tenant_id / str(pkg.package_id))


def test_batch_source_happy_path_tar_gz(phase_1b_storage_root: Path) -> None:
    """tar.gz archive with two files → two IntakePackages, bytes materialized."""
    tenant_id = f"tenant-e2e-batch-targz-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_targz_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(storage_root=storage_root, tenant_id=tenant_id)
    files = {"alpha.csv": b"a,1\nb,2\n", "report.txt": b"summary line"}
    data = _make_tar_gz(files)

    pkgs = adapter.enqueue(raw_bytes=data, filename="daily.tar.gz")
    assert len(pkgs) == 2
    by_name = {p.files[0].file_name: p for p in pkgs}
    for name, payload in files.items():
        pkg = by_name[name]
        assert isinstance(pkg, IntakePackage)
        assert Path(pkg.files[0].file_path).read_bytes() == payload


def test_batch_source_zip_bomb_guard_rejects_high_ratio(
    phase_1b_storage_root: Path,
) -> None:
    """Highly compressible payload exceeding max_compression_ratio → SourceAdapterError."""
    tenant_id = f"tenant-e2e-batch-bomb-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_bomb_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_compression_ratio=2.0,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.bin", b"\x00" * 100_000)
    data = buf.getvalue()

    with pytest.raises(SourceAdapterError, match="zip-bomb guard"):
        adapter.enqueue(raw_bytes=data, filename="bomb.zip")

    tenant_dir = storage_root / tenant_id
    if tenant_dir.exists():
        leaked = [p for p in tenant_dir.rglob("bomb.bin") if p.is_file()]
        assert leaked == []


def test_batch_source_path_traversal_entry_dropped(
    phase_1b_storage_root: Path,
) -> None:
    """ZIP entry with ../ path components is skipped (not written under storage)."""
    tenant_id = f"tenant-e2e-batch-traverse-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_traverse_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(storage_root=storage_root, tenant_id=tenant_id)
    data = _make_zip(
        {
            "../../etc/passwd": b"root:x:0:0:",
            "safe.txt": b"clean",
        }
    )
    pkgs = adapter.enqueue(raw_bytes=data, filename="traversal.zip")
    assert len(pkgs) == 1
    assert pkgs[0].files[0].file_name == "safe.txt"

    leaked_passwd = list((storage_root).rglob("passwd"))
    assert leaked_passwd == [], f"traversal entry leaked: {leaked_passwd}"


def test_batch_source_empty_archive_after_filter_raises(
    phase_1b_storage_root: Path,
) -> None:
    """Archive that yields zero extractable files after the glob filter → SourceAdapterError."""
    tenant_id = f"tenant-e2e-batch-empty-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_empty_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        glob_patterns=["*.pdf"],
    )
    data = _make_zip({"only-text.txt": b"nothing pdf here"})

    with pytest.raises(SourceAdapterError, match="no extractable files"):
        adapter.enqueue(raw_bytes=data, filename="no-pdf.zip")


def test_batch_source_oversize_archive_rejected(
    phase_1b_storage_root: Path,
) -> None:
    """Archive raw size above max_archive_bytes → SourceAdapterError before unpack."""
    tenant_id = f"tenant-e2e-batch-oversize-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_oversize_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_archive_bytes=64,
    )
    data = _make_zip({"big.bin": b"X" * 10_000})
    assert len(data) > 64

    with pytest.raises(SourceAdapterError, match="exceeds max_archive_bytes"):
        adapter.enqueue(raw_bytes=data, filename="too-big.zip")

    tenant_dir = storage_root / tenant_id
    if tenant_dir.exists():
        leaked = [p for p in tenant_dir.rglob("big.bin") if p.is_file()]
        assert leaked == []


@pytest.mark.asyncio
async def test_batch_source_acknowledge_reject_and_health_check(
    phase_1b_storage_root: Path,
) -> None:
    """Happy archive → fetch_next lifecycle + ack/reject + health_check."""
    tenant_id = f"tenant-e2e-batch-ack-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"batch_ack_{uuid4().hex[:8]}"

    adapter = BatchSourceAdapter(storage_root=storage_root, tenant_id=tenant_id)
    assert await adapter.health_check() is True

    data = _make_zip({"one.txt": b"1", "two.txt": b"2"})
    pkgs = adapter.enqueue(raw_bytes=data, filename="pair.zip")
    assert len(pkgs) == 2

    first = await adapter.fetch_next()
    second = await adapter.fetch_next()
    assert first is not None and second is not None
    assert await adapter.fetch_next() is None

    await adapter.acknowledge(first.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(first.package_id)

    await adapter.reject(second.package_id, reason="e2e-test")
    with pytest.raises(SourceAdapterError):
        await adapter.reject(second.package_id, reason="double-reject")
