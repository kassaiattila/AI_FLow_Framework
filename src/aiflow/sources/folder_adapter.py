"""FolderSourceAdapter — pull-mode file-system watcher producing IntakePackage.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md R1 (FolderSourceAdapter),
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 2 Day 6 — E2.1).

Uses `watchdog.observers.Observer` to receive file-system events for a watched
directory, then applies three guards before emitting an IntakePackage:

* **Debounce** — a path must be "quiet" for `debounce_ms` after the last
  event before we consider it for processing (editors often emit several
  CREATE/MODIFY bursts for a single save).
* **Mid-write guard** — two ``os.stat`` samples taken
  ``stable_mtime_window_ms`` apart must show identical size + mtime before
  we read the file, so partial copies (``*.crdownload``, half-written PDFs)
  are skipped until stable.
* **Glob / excluded filter** — only files matching ``glob_patterns`` are
  admitted; paths matching ``excluded_patterns`` are dropped before being
  queued.

Each stabilised file yields exactly one IntakePackage with exactly one
IntakeFile. Multi-file "folder batches" are the responsibility of the
association layer (N4, E3.x) and are out of scope here.

Per-file errors (PermissionError, OSError, missing file) are logged as
warnings and never raised across the adapter boundary — one broken file must
not take the whole folder-watch down. Only policy violations (size guard)
propagate as ``SourceAdapterError``.
"""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import mimetypes
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID, uuid4

import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from aiflow.intake.package import (
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources._fs import sanitize_filename
from aiflow.sources.base import SourceAdapter, SourceAdapterMetadata
from aiflow.sources.exceptions import SourceAdapterError

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

__all__ = [
    "FolderSourceAdapter",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MIME = "application/octet-stream"
_DEFAULT_GLOB: tuple[str, ...] = ("*",)
_DEFAULT_EXCLUDED: tuple[str, ...] = (
    ".~*",
    "~$*",
    "*.partial",
    "*.crdownload",
    "*.tmp",
    "*.swp",
)


def _default_mime_detect(_payload: bytes, filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or _DEFAULT_MIME


class _FolderEventHandler(FileSystemEventHandler):
    """Routes watchdog events into the adapter's pending map."""

    def __init__(self, adapter: FolderSourceAdapter) -> None:
        self._adapter = adapter

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._adapter._note_event(Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._adapter._note_event(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", None)
        if dest:
            self._adapter._note_event(Path(dest))


class FolderSourceAdapter(SourceAdapter):
    """Pull-mode adapter that converts files appearing in a watched folder
    into single-file IntakePackages.

    Storage policy mirrors :class:`FileSourceAdapter`: every package gets a
    fresh UUID, and the copy lives at
    ``storage_root/{tenant_id}/{package_id}/{sanitized_filename}``. The
    original file under ``watch_root`` is left in place — moving / archiving
    the source is the responsibility of a later ingestion step.
    """

    source_type: ClassVar[IntakeSourceType] = IntakeSourceType.FOLDER_IMPORT

    def __init__(
        self,
        *,
        watch_root: Path | str,
        storage_root: Path | str,
        tenant_id: str,
        debounce_ms: int = 500,
        stable_mtime_window_ms: int = 1_000,
        max_package_bytes: int | None = None,
        glob_patterns: list[str] | None = None,
        excluded_patterns: list[str] | None = None,
        adapter_name: str = "folder_import",
        adapter_version: str = "0.1.0",
        mime_detect: Callable[[bytes, str], str] | None = None,
        observer_factory: Callable[[], BaseObserver] | None = None,
        auto_start: bool = True,
    ) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        if debounce_ms < 0 or stable_mtime_window_ms < 0:
            raise ValueError("debounce_ms and stable_mtime_window_ms must be non-negative")

        self._watch_root = Path(watch_root)
        self._storage_root = Path(storage_root)
        self._tenant_id = tenant_id
        self._debounce_s = debounce_ms / 1000.0
        self._stable_window_s = stable_mtime_window_ms / 1000.0
        self._max_package_bytes = max_package_bytes
        self._glob_patterns = list(glob_patterns) if glob_patterns else list(_DEFAULT_GLOB)
        self._excluded_patterns = (
            list(excluded_patterns) if excluded_patterns is not None else list(_DEFAULT_EXCLUDED)
        )
        self._adapter_name = adapter_name
        self._adapter_version = adapter_version
        self._mime_detect = mime_detect or _default_mime_detect
        self._observer_factory = observer_factory or Observer

        self._lock = threading.Lock()
        self._pending: dict[Path, float] = {}
        self._queue: deque[IntakePackage] = deque()
        self._in_flight: dict[UUID, IntakePackage] = {}
        self._observer: BaseObserver | None = None

        if auto_start:
            self._start_observer()

    # --- Observer lifecycle ---------------------------------------------

    def _start_observer(self) -> None:
        if self._observer is not None:
            return
        if not self._watch_root.is_dir():
            logger.warning(
                "folder_adapter_watch_root_missing",
                watch_root=str(self._watch_root),
            )
            return
        observer = self._observer_factory()
        handler = _FolderEventHandler(self)
        observer.schedule(handler, str(self._watch_root), recursive=False)
        observer.start()
        self._observer = observer
        logger.info(
            "folder_adapter_started",
            watch_root=str(self._watch_root),
            debounce_ms=int(self._debounce_s * 1000),
            stable_window_ms=int(self._stable_window_s * 1000),
        )

    def close(self) -> None:
        observer = self._observer
        self._observer = None
        if observer is None:
            return
        try:
            observer.stop()
            observer.join(timeout=5.0)
        except Exception:
            logger.warning("folder_adapter_observer_stop_failed", exc_info=True)
        logger.info("folder_adapter_stopped")

    def __enter__(self) -> FolderSourceAdapter:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    async def __aenter__(self) -> FolderSourceAdapter:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        self.close()

    # --- Event ingestion (called from the observer thread) --------------

    def _note_event(self, path: Path) -> None:
        if self._is_excluded(path.name):
            return
        if not self._matches_glob(path.name):
            return
        with self._lock:
            self._pending[path] = time.monotonic()

    def _is_excluded(self, filename: str) -> bool:
        return any(fnmatch.fnmatch(filename, pat) for pat in self._excluded_patterns)

    def _matches_glob(self, filename: str) -> bool:
        return any(fnmatch.fnmatch(filename, pat) for pat in self._glob_patterns)

    # --- SourceAdapter contract -----------------------------------------

    @property
    def metadata(self) -> SourceAdapterMetadata:
        return SourceAdapterMetadata(
            name=self._adapter_name,
            version=self._adapter_version,
            source_type=IntakeSourceType.FOLDER_IMPORT,
            transport="pull",
            requires_ack=False,
            supports_batching=False,
            max_package_bytes=self._max_package_bytes,
        )

    async def fetch_next(self) -> IntakePackage | None:
        await self._drain_pending()
        if not self._queue:
            return None
        return self._queue.popleft()

    async def acknowledge(self, package_id: UUID) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot acknowledge (not in-flight)"
            )
        self._in_flight.pop(package_id, None)
        logger.info("folder_adapter_acknowledged", package_id=str(package_id))

    async def reject(self, package_id: UUID, reason: str) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot reject (not in-flight)"
            )
        self._in_flight.pop(package_id, None)
        logger.info("folder_adapter_rejected", package_id=str(package_id), reason=reason)

    async def health_check(self) -> bool:
        if not self._watch_root.is_dir():
            return False
        if self._observer is None:
            return False
        return bool(self._observer.is_alive())

    # --- Drain pipeline --------------------------------------------------

    async def _drain_pending(self) -> None:
        now = time.monotonic()
        with self._lock:
            ripe: list[Path] = [p for p, t in self._pending.items() if now - t >= self._debounce_s]
        for path in ripe:
            await self._process_ripe(path)

    async def _process_ripe(self, path: Path) -> None:
        try:
            first = path.stat()
        except FileNotFoundError:
            with self._lock:
                self._pending.pop(path, None)
            return
        except (PermissionError, OSError) as exc:
            logger.warning(
                "folder_adapter_stat_failed",
                path=str(path),
                error=type(exc).__name__,
            )
            with self._lock:
                self._pending.pop(path, None)
            return

        if self._stable_window_s > 0:
            await asyncio.sleep(self._stable_window_s)
            try:
                second = path.stat()
            except (FileNotFoundError, PermissionError, OSError) as exc:
                logger.warning(
                    "folder_adapter_stat_second_failed",
                    path=str(path),
                    error=type(exc).__name__,
                )
                with self._lock:
                    self._pending.pop(path, None)
                return

            if second.st_size != first.st_size or second.st_mtime != first.st_mtime:
                with self._lock:
                    self._pending[path] = time.monotonic()
                logger.info(
                    "folder_adapter_unstable_retry",
                    path=str(path),
                    size_before=first.st_size,
                    size_after=second.st_size,
                )
                return
            size = second.st_size
        else:
            size = first.st_size

        if self._max_package_bytes is not None and size > self._max_package_bytes:
            with self._lock:
                self._pending.pop(path, None)
            logger.info(
                "folder_adapter_size_exceeded",
                path=str(path),
                size_bytes=size,
                max_package_bytes=self._max_package_bytes,
            )
            raise SourceAdapterError(
                f"folder file {path.name!r} is {size} bytes; exceeds max_package_bytes="
                f"{self._max_package_bytes}"
            )

        try:
            payload = path.read_bytes()
        except (FileNotFoundError, PermissionError, OSError) as exc:
            logger.warning(
                "folder_adapter_read_failed",
                path=str(path),
                error=type(exc).__name__,
            )
            with self._lock:
                self._pending.pop(path, None)
            return

        resolved_mime = self._mime_detect(payload, path.name)

        package_id = uuid4()
        safe = sanitize_filename(path.name)
        pkg_dir = self._storage_root / self._tenant_id / str(package_id)
        try:
            pkg_dir.mkdir(parents=True, exist_ok=True)
            dest = pkg_dir / safe
            dest.write_bytes(payload)
        except (PermissionError, OSError) as exc:
            logger.warning(
                "folder_adapter_spill_failed",
                path=str(path),
                error=type(exc).__name__,
            )
            with self._lock:
                self._pending.pop(path, None)
            return

        intake_file = IntakeFile(
            file_path=str(dest),
            file_name=path.name,
            mime_type=resolved_mime,
            size_bytes=size,
            sha256=hashlib.sha256(payload).hexdigest(),
            sequence_index=0,
            source_metadata={
                "watch_root": str(self._watch_root),
                "original_path": str(path),
                "sanitized_filename": safe,
            },
        )

        pkg = IntakePackage(
            package_id=package_id,
            source_type=IntakeSourceType.FOLDER_IMPORT,
            tenant_id=self._tenant_id,
            source_metadata={
                "watch_root": str(self._watch_root),
                "original_path": str(path),
                "mime_type": resolved_mime,
            },
            files=[intake_file],
        )

        with self._lock:
            self._pending.pop(path, None)
        self._queue.append(pkg)
        self._in_flight[package_id] = pkg
        logger.info(
            "folder_adapter_enqueued",
            package_id=str(package_id),
            path=str(path),
            size_bytes=size,
            mime_type=resolved_mime,
        )
