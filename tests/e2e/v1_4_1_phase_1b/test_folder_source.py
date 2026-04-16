"""E2E — FolderSourceAdapter (Phase 1b Week 2 Day 10 / E2.4).

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, intake, source_adapter, folder_import]

Real pipeline: FolderSourceAdapter drives against a real tmp watch root +
real storage spill. The watchdog ``Observer`` is driven synthetically via
``_note_event`` in most cases for deterministic ticks; a dedicated test
exercises the real observer end-to-end.

DB persistence round-trip is intentionally out of scope — per
feedback_asyncpg_pool_event_loop.md the module-level asyncpg pool is bound
to the first event loop, so multiple function-scoped async tests reaching
for the pool crash with InterfaceError. This file stays storage-only.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import IntakePackage, IntakeSourceType
from aiflow.sources import FolderSourceAdapter, SourceAdapterError
from aiflow.sources._fs import sanitize_filename
from aiflow.sources.registry import SourceAdapterRegistry


@pytest.mark.asyncio
async def test_folder_source_happy_path_emits_intake_package(
    phase_1b_storage_root: Path,
    phase_1b_source_registry: SourceAdapterRegistry,
) -> None:
    """File drop → debounce window → single IntakePackage with sha256 + real spill."""
    tenant_id = f"tenant-e2e-folder-happy-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_happy_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_happy_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=30,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    phase_1b_source_registry.register(FolderSourceAdapter)
    assert phase_1b_source_registry.has(IntakeSourceType.FOLDER_IMPORT)

    payload = b"%PDF-1.4 folder e2e payload\n"
    path = watch_root / "invoice.pdf"
    path.write_bytes(payload)
    adapter._note_event(path)

    assert await adapter.fetch_next() is None, "must not emit inside debounce window"
    await asyncio.sleep(0.05)

    pkg = await adapter.fetch_next()
    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.FOLDER_IMPORT
    assert pkg.tenant_id == tenant_id
    assert len(pkg.files) == 1
    intake_file = pkg.files[0]
    assert intake_file.file_name == "invoice.pdf"
    assert intake_file.sha256 == hashlib.sha256(payload).hexdigest()
    assert intake_file.size_bytes == len(payload)

    on_disk = Path(intake_file.file_path)
    assert on_disk.exists()
    assert on_disk.read_bytes() == payload
    assert on_disk.is_relative_to(storage_root / tenant_id / str(pkg.package_id))


@pytest.mark.asyncio
async def test_folder_source_mid_write_guard_skips_growing_file(
    phase_1b_storage_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mid-write file (size changes between stats) is not emitted and is re-armed."""
    tenant_id = f"tenant-e2e-folder-midwrite-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_midwrite_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_midwrite_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=10,
        auto_start=False,
    )
    path = watch_root / "growing.bin"
    path.write_bytes(b"short")

    real_stat = Path.stat
    calls = {"n": 0}

    class _FakeStat:
        def __init__(self, size: int, mtime: float) -> None:
            self.st_size = size
            self.st_mtime = mtime

    def fake_stat(self: Path, *args, **kwargs):
        if self != path:
            return real_stat(self, *args, **kwargs)
        calls["n"] += 1
        return _FakeStat(100 if calls["n"] == 1 else 200, 1000.0 + calls["n"])

    monkeypatch.setattr(Path, "stat", fake_stat)
    adapter._note_event(path)

    assert await adapter.fetch_next() is None, "unstable file must be skipped"
    assert path in adapter._pending, "unstable file must be re-armed for next drain"


@pytest.mark.asyncio
async def test_folder_source_yields_after_stabilization(
    phase_1b_storage_root: Path,
) -> None:
    """Two consecutive stable stats (size+mtime identical) → file emitted."""
    tenant_id = f"tenant-e2e-folder-stable-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_stable_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_stable_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=20,
        auto_start=False,
    )
    payload = b"stabilized content"
    path = watch_root / "stable.bin"
    path.write_bytes(payload)

    adapter._note_event(path)
    pkg = await adapter.fetch_next()
    assert isinstance(pkg, IntakePackage)
    assert pkg.files[0].sha256 == hashlib.sha256(payload).hexdigest()
    assert Path(pkg.files[0].file_path).read_bytes() == payload
    assert path not in adapter._pending


@pytest.mark.asyncio
async def test_folder_source_sanitizes_path_traversal_filename(
    phase_1b_storage_root: Path,
) -> None:
    """Unsafe filename components (parens/spaces) collapse via sanitize_filename."""
    tenant_id = f"tenant-e2e-folder-sanitize-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_sanitize_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_sanitize_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    unsafe_name = "weird name (draft).pdf"
    payload = b"sanitize canary"
    path = watch_root / unsafe_name
    path.write_bytes(payload)
    adapter._note_event(path)

    pkg = await adapter.fetch_next()
    assert pkg is not None
    spilled = Path(pkg.files[0].file_path)
    expected_safe = sanitize_filename(unsafe_name)
    assert spilled.name == expected_safe
    assert expected_safe != unsafe_name
    assert pkg.files[0].file_name == unsafe_name  # original preserved
    assert spilled.is_relative_to(storage_root / tenant_id / str(pkg.package_id))


@pytest.mark.asyncio
async def test_folder_source_size_guard_rejects_oversize(
    phase_1b_storage_root: Path,
) -> None:
    """File larger than max_package_bytes → SourceAdapterError, no storage spill."""
    tenant_id = f"tenant-e2e-folder-oversize-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_oversize_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_oversize_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=0,
        max_package_bytes=16,
        auto_start=False,
    )
    path = watch_root / "too-big.bin"
    path.write_bytes(b"X" * 4096)
    adapter._note_event(path)

    with pytest.raises(SourceAdapterError, match="exceeds max_package_bytes"):
        await adapter.fetch_next()

    tenant_dir = storage_root / tenant_id
    if tenant_dir.exists():
        leaked = [p for p in tenant_dir.rglob("too-big.bin") if p.is_file()]
        assert leaked == [], f"oversize bytes leaked onto disk: {leaked}"
    assert path not in adapter._pending


@pytest.mark.asyncio
async def test_folder_source_health_check_true_for_writable_root(
    phase_1b_storage_root: Path,
) -> None:
    """A live Observer watching an existing root → health_check True."""
    tenant_id = f"tenant-e2e-folder-health-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_health_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_health_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        auto_start=True,
    )
    try:
        assert await adapter.health_check() is True
    finally:
        adapter.close()
    assert await adapter.health_check() is False


@pytest.mark.asyncio
async def test_folder_source_acknowledge_and_reject_lifecycle(
    phase_1b_storage_root: Path,
) -> None:
    """Successful acknowledge + reject bookkeeping; double-ack raises."""
    tenant_id = f"tenant-e2e-folder-ack-{uuid4().hex[:8]}"
    watch_root = phase_1b_storage_root / f"folder_ack_watch_{uuid4().hex[:8]}"
    watch_root.mkdir(parents=True, exist_ok=True)
    storage_root = phase_1b_storage_root / f"folder_ack_storage_{uuid4().hex[:8]}"

    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    (watch_root / "a.txt").write_bytes(b"a")
    (watch_root / "b.txt").write_bytes(b"b")
    adapter._note_event(watch_root / "a.txt")
    adapter._note_event(watch_root / "b.txt")

    pkg_a = await adapter.fetch_next()
    pkg_b = await adapter.fetch_next()
    assert pkg_a is not None and pkg_b is not None
    assert pkg_a.package_id != pkg_b.package_id

    await adapter.acknowledge(pkg_a.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg_a.package_id)

    await adapter.reject(pkg_b.package_id, reason="e2e-test")
    with pytest.raises(SourceAdapterError):
        await adapter.reject(pkg_b.package_id, reason="double-reject")
