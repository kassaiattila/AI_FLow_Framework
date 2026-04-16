"""Unit tests for FolderSourceAdapter (Phase 1b — Week 2 Day 6 — E2.1).

@test_registry: phase_1b.sources.folder_adapter

Covers metadata shape, debounce → mid-write-guard → enqueue flow, glob +
excluded filters, sha256/size/sanitize, size guard, ack/reject bookkeeping,
PermissionError handling, health_check, close() lifecycle and dedup.

Most tests drive the adapter through `_note_event` so the real watchdog
Observer is not started — this keeps the suite fast and deterministic. One
dedicated test (``test_close_stops_observer_thread``) exercises the real
Observer lifecycle, and one end-to-end test verifies that the watchdog
handler is wired up correctly.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import IntakePackage, IntakeSourceType
from aiflow.sources import FolderSourceAdapter, SourceAdapterError
from aiflow.sources._fs import sanitize_filename

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def watch_root(tmp_path: Path) -> Path:
    root = tmp_path / "watch"
    root.mkdir()
    return root


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def _make_adapter(
    *,
    watch_root: Path,
    storage_root: Path,
    tenant_id: str = "tenant_a",
    debounce_ms: int = 0,
    stable_mtime_window_ms: int = 0,
    max_package_bytes: int | None = None,
    glob_patterns: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
    auto_start: bool = False,
    mime_detect=None,
    observer_factory=None,
) -> FolderSourceAdapter:
    return FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=debounce_ms,
        stable_mtime_window_ms=stable_mtime_window_ms,
        max_package_bytes=max_package_bytes,
        glob_patterns=glob_patterns,
        excluded_patterns=excluded_patterns,
        auto_start=auto_start,
        mime_detect=mime_detect,
        observer_factory=observer_factory,
    )


# ---------------------------------------------------------------------------
# 1. Metadata shape
# ---------------------------------------------------------------------------


def test_metadata_shape(watch_root: Path, storage_root: Path) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    meta = adapter.metadata
    assert meta.source_type == IntakeSourceType.FOLDER_IMPORT
    assert meta.transport == "pull"
    assert meta.requires_ack is False
    assert meta.supports_batching is False
    assert meta.name == "folder_import"
    assert FolderSourceAdapter.source_type == IntakeSourceType.FOLDER_IMPORT


# ---------------------------------------------------------------------------
# 2. Empty folder → fetch_next() is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_folder_fetch_returns_none(watch_root: Path, storage_root: Path) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    assert await adapter.fetch_next() is None


# ---------------------------------------------------------------------------
# 3. New file → after debounce → IntakePackage with one IntakeFile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_note_event_after_debounce_emits_single_file_package(
    watch_root: Path, storage_root: Path
) -> None:
    adapter = _make_adapter(
        watch_root=watch_root,
        storage_root=storage_root,
        debounce_ms=30,
        stable_mtime_window_ms=0,
    )
    path = watch_root / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 dummy")
    adapter._note_event(path)

    # Under the debounce window → still quiet.
    first = await adapter.fetch_next()
    assert first is None

    await asyncio.sleep(0.05)
    pkg = await adapter.fetch_next()
    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.FOLDER_IMPORT
    assert pkg.tenant_id == "tenant_a"
    assert len(pkg.files) == 1
    assert pkg.files[0].file_name == "doc.pdf"


# ---------------------------------------------------------------------------
# 4. sha256 + size_bytes computed correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sha256_and_size_bytes_are_correct(watch_root: Path, storage_root: Path) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    payload = b"hello folder adapter" * 16
    path = watch_root / "data.bin"
    path.write_bytes(payload)
    adapter._note_event(path)

    pkg = await adapter.fetch_next()
    assert pkg is not None
    f = pkg.files[0]
    assert f.size_bytes == len(payload)
    assert f.sha256 == hashlib.sha256(payload).hexdigest()
    # Storage spill actually carries the bytes, not a reference to the source.
    assert Path(f.file_path).read_bytes() == payload


# ---------------------------------------------------------------------------
# 5. sanitize_filename helper is applied to the spilled filename
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsafe_filename_is_sanitized_via_helper(
    watch_root: Path, storage_root: Path
) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    # Spaces + parens are not in the safe [A-Za-z0-9._-] set.
    unsafe_name = "weird name (draft).pdf"
    path = watch_root / unsafe_name
    path.write_bytes(b"x")
    adapter._note_event(path)

    pkg = await adapter.fetch_next()
    assert pkg is not None
    spilled = Path(pkg.files[0].file_path)
    expected_safe = sanitize_filename(unsafe_name)
    assert spilled.name == expected_safe
    assert expected_safe != unsafe_name
    assert pkg.files[0].file_name == unsafe_name  # original preserved on Pydantic


# ---------------------------------------------------------------------------
# 6. glob_patterns filter — *.pdf admits a PDF, blocks a TXT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_glob_patterns_filter_excludes_non_matching(
    watch_root: Path, storage_root: Path
) -> None:
    adapter = _make_adapter(
        watch_root=watch_root,
        storage_root=storage_root,
        glob_patterns=["*.pdf"],
    )
    pdf = watch_root / "ok.pdf"
    pdf.write_bytes(b"x")
    txt = watch_root / "skip.txt"
    txt.write_bytes(b"y")

    adapter._note_event(pdf)
    adapter._note_event(txt)
    # Only PDF should be pending.
    assert pdf in adapter._pending
    assert txt not in adapter._pending

    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert pkg.files[0].file_name == "ok.pdf"
    assert await adapter.fetch_next() is None


# ---------------------------------------------------------------------------
# 7. excluded_patterns — default excludes *.partial / *.crdownload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_excluded_patterns_block_partial_and_crdownload(
    watch_root: Path, storage_root: Path
) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    partial = watch_root / "report.partial"
    cr = watch_root / "firefox.crdownload"
    ok = watch_root / "final.pdf"
    for p in (partial, cr, ok):
        p.write_bytes(b"x")

    adapter._note_event(partial)
    adapter._note_event(cr)
    adapter._note_event(ok)

    assert partial not in adapter._pending
    assert cr not in adapter._pending
    assert ok in adapter._pending

    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert pkg.files[0].file_name == "final.pdf"


# ---------------------------------------------------------------------------
# 8. Mid-write guard — size changes between stats → no package, re-stamped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mid_write_guard_skips_unstable_file(
    watch_root: Path, storage_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _make_adapter(
        watch_root=watch_root,
        storage_root=storage_root,
        debounce_ms=0,
        stable_mtime_window_ms=10,
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
        # First sample: 100 bytes. Second sample: 200 bytes → unstable.
        return _FakeStat(100 if calls["n"] == 1 else 200, 1000.0 + calls["n"])

    monkeypatch.setattr(Path, "stat", fake_stat)
    adapter._note_event(path)

    pkg = await adapter.fetch_next()
    assert pkg is None  # still growing → skipped this round
    # Path re-armed for the next drain.
    assert path in adapter._pending


# ---------------------------------------------------------------------------
# 9. max_package_bytes overflow → SourceAdapterError, no storage spill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_size_guard_raises_and_no_storage_spill(watch_root: Path, storage_root: Path) -> None:
    adapter = _make_adapter(
        watch_root=watch_root,
        storage_root=storage_root,
        max_package_bytes=16,
    )
    path = watch_root / "too-big.bin"
    path.write_bytes(b"X" * 64)
    adapter._note_event(path)

    with pytest.raises(SourceAdapterError, match="exceeds max_package_bytes"):
        await adapter.fetch_next()
    # Nothing spilled under storage_root.
    assert not storage_root.exists() or not any(storage_root.rglob("too-big.bin"))
    # Path was removed from pending so subsequent calls don't re-raise endlessly.
    assert path not in adapter._pending


# ---------------------------------------------------------------------------
# 10. acknowledge(unknown) → SourceAdapterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_unknown_package_id_raises(watch_root: Path, storage_root: Path) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(uuid4())


# ---------------------------------------------------------------------------
# 11. acknowledge idempotens — double-ack raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_idempotent_double_ack_raises(
    watch_root: Path, storage_root: Path
) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    path = watch_root / "a.txt"
    path.write_bytes(b"x")
    adapter._note_event(path)

    pkg = await adapter.fetch_next()
    assert pkg is not None
    await adapter.acknowledge(pkg.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg.package_id)


# ---------------------------------------------------------------------------
# 12. reject(unknown) → SourceAdapterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_unknown_package_id_raises(watch_root: Path, storage_root: Path) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.reject(uuid4(), reason="nope")


# ---------------------------------------------------------------------------
# 13. PermissionError during read → warning logged + no package + no crash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_permission_error_yields_no_package(
    watch_root: Path,
    storage_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _make_adapter(watch_root=watch_root, storage_root=storage_root)
    locked = watch_root / "locked.txt"
    locked.write_bytes(b"secret")

    real_read = Path.read_bytes

    def fake_read(self: Path, *args, **kwargs) -> bytes:
        if self == locked:
            raise PermissionError("access denied")
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", fake_read)

    adapter._note_event(locked)
    pkg = await adapter.fetch_next()
    assert pkg is None
    # Path cleared from pending even though read failed — we don't loop forever.
    assert locked not in adapter._pending
    # No storage spill for the failed file.
    tenant_dir = storage_root / "tenant_a"
    if tenant_dir.exists():
        assert not any(tenant_dir.rglob("locked.txt"))


# ---------------------------------------------------------------------------
# 14. health_check False when watch_root does not exist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_false_when_watch_root_missing(
    tmp_path: Path, storage_root: Path
) -> None:
    missing = tmp_path / "never_created"
    adapter = FolderSourceAdapter(
        watch_root=missing,
        storage_root=storage_root,
        tenant_id="t",
        auto_start=False,
    )
    assert await adapter.health_check() is False


# ---------------------------------------------------------------------------
# 15. close() stops the real observer thread
# ---------------------------------------------------------------------------


def test_close_stops_observer_thread(watch_root: Path, storage_root: Path) -> None:
    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id="t",
        auto_start=True,
    )
    observer = adapter._observer
    assert observer is not None
    assert observer.is_alive()

    adapter.close()
    # The observer thread joined; reference is cleared on the adapter.
    assert adapter._observer is None
    # Small grace period — join was already called, but be robust across platforms.
    for _ in range(20):
        if not observer.is_alive():
            break
        time.sleep(0.05)
    assert not observer.is_alive()


# ---------------------------------------------------------------------------
# 16. Dedup — multiple events within the debounce window produce one package
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_events_within_debounce_window_yield_one_package(
    watch_root: Path, storage_root: Path
) -> None:
    adapter = _make_adapter(
        watch_root=watch_root,
        storage_root=storage_root,
        debounce_ms=20,
    )
    path = watch_root / "dup.txt"
    path.write_bytes(b"hello")
    adapter._note_event(path)
    adapter._note_event(path)
    adapter._note_event(path)
    assert len(adapter._pending) == 1

    await asyncio.sleep(0.05)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    # No second package in the queue.
    assert await adapter.fetch_next() is None


# ---------------------------------------------------------------------------
# 17. tenant_id blank → ValueError at construction
# ---------------------------------------------------------------------------


def test_empty_tenant_id_rejected(watch_root: Path, storage_root: Path) -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        FolderSourceAdapter(
            watch_root=watch_root,
            storage_root=storage_root,
            tenant_id="",
            auto_start=False,
        )


# ---------------------------------------------------------------------------
# 18. End-to-end: real Observer picks up a file creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_observer_detects_created_file(watch_root: Path, storage_root: Path) -> None:
    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id="tenant_a",
        debounce_ms=30,
        stable_mtime_window_ms=20,
        auto_start=True,
    )
    try:
        path = watch_root / "e2e.pdf"
        path.write_bytes(b"%PDF-1.4 e2e")

        pkg: IntakePackage | None = None
        for _ in range(40):  # up to ~2s total
            await asyncio.sleep(0.05)
            pkg = await adapter.fetch_next()
            if pkg is not None:
                break
        assert pkg is not None, "watchdog Observer did not surface the created file"
        assert pkg.files[0].file_name == "e2e.pdf"
    finally:
        adapter.close()


# ---------------------------------------------------------------------------
# 19. Invalid negative debounce / stable-window rejected
# ---------------------------------------------------------------------------


def test_negative_timings_rejected(watch_root: Path, storage_root: Path) -> None:
    with pytest.raises(ValueError, match="debounce_ms"):
        FolderSourceAdapter(
            watch_root=watch_root,
            storage_root=storage_root,
            tenant_id="t",
            debounce_ms=-1,
            auto_start=False,
        )
