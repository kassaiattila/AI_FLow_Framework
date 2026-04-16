"""BatchSourceAdapter — push-mode archive source producing per-file IntakePackages.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md R1,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 2 Day 7 — E2.2).

Accepts ZIP or tar(.gz/.bz2/.xz) archives via ``enqueue()``, unpacks them
into per-tenant storage, and emits one IntakePackage per extracted file.

Security guards:
* **Zip-bomb**: ``uncompressed_total / archive_size > max_compression_ratio`` → reject.
* **Symlink / path traversal**: entries containing ``..`` or absolute paths
  are skipped (warning logged).
* **Max archive bytes**: archives above the threshold are rejected before any
  I/O beyond a stat() call.
* **Max file count**: if the archive contains more extractable files than
  ``max_file_count``, the whole archive is rejected.
* **Corrupt archive**: ``zipfile.BadZipFile`` / ``tarfile.TarError`` → reject.
"""

from __future__ import annotations

import hashlib
import io
import mimetypes
import os
import tarfile
import zipfile
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar
from uuid import UUID, uuid4

import structlog

from aiflow.intake.package import (
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources._fs import sanitize_filename
from aiflow.sources.base import SourceAdapter, SourceAdapterMetadata
from aiflow.sources.exceptions import SourceAdapterError

__all__ = [
    "BatchSourceAdapter",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MIME = "application/octet-stream"
_DEFAULT_EXCLUDED: tuple[str, ...] = (
    "*.tmp",
    "*.swp",
    ".DS_Store",
    "Thumbs.db",
    "__MACOSX/*",
)


def _default_mime_detect(_payload: bytes, filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or _DEFAULT_MIME


def _is_path_traversal(member_name: str) -> bool:
    normalized = os.path.normpath(member_name)
    return normalized.startswith("..") or os.path.isabs(normalized)


class BatchSourceAdapter(SourceAdapter):
    """Push-mode adapter: unpack a ZIP/tar archive into per-file IntakePackages.

    Each call to ``enqueue()`` accepts a single archive (via ``archive_path``
    or ``raw_bytes``), validates it against the configured guards, unpacks it
    to per-package storage dirs, and returns the list of produced packages.
    Packages are also buffered in an internal queue for ``fetch_next()``
    consumption.
    """

    source_type: ClassVar[IntakeSourceType] = IntakeSourceType.BATCH_IMPORT

    def __init__(
        self,
        *,
        storage_root: Path | str,
        tenant_id: str,
        max_archive_bytes: int = 500_000_000,
        max_file_count: int = 100,
        max_compression_ratio: float = 50.0,
        glob_patterns: list[str] | None = None,
        excluded_patterns: list[str] | None = None,
        adapter_name: str = "batch_import",
        adapter_version: str = "0.1.0",
        mime_detect: Callable[[bytes, str], str] | None = None,
    ) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        self._storage_root = Path(storage_root)
        self._tenant_id = tenant_id
        self._max_archive_bytes = max_archive_bytes
        self._max_file_count = max_file_count
        self._max_compression_ratio = max_compression_ratio
        self._glob_patterns = list(glob_patterns) if glob_patterns else ["*"]
        self._excluded_patterns = (
            list(excluded_patterns) if excluded_patterns is not None else list(_DEFAULT_EXCLUDED)
        )
        self._adapter_name = adapter_name
        self._adapter_version = adapter_version
        self._mime_detect = mime_detect or _default_mime_detect

        self._queue: deque[IntakePackage] = deque()
        self._in_flight: dict[UUID, IntakePackage] = {}

    @property
    def metadata(self) -> SourceAdapterMetadata:
        return SourceAdapterMetadata(
            name=self._adapter_name,
            version=self._adapter_version,
            source_type=IntakeSourceType.BATCH_IMPORT,
            transport="push",
            requires_ack=False,
            supports_batching=True,
            max_package_bytes=self._max_archive_bytes,
        )

    # --- enqueue -----------------------------------------------------------

    def enqueue(
        self,
        *,
        archive_path: Path | str | None = None,
        raw_bytes: bytes | None = None,
        filename: str,
    ) -> list[IntakePackage]:
        if not filename:
            raise ValueError("filename must be non-empty")
        if (archive_path is None) == (raw_bytes is None):
            raise ValueError("exactly one of archive_path or raw_bytes must be provided")

        if raw_bytes is None:
            assert archive_path is not None
            src = Path(archive_path)
            archive_size = src.stat().st_size
            if archive_size > self._max_archive_bytes:
                raise SourceAdapterError(
                    f"archive {filename!r} is {archive_size} bytes; "
                    f"exceeds max_archive_bytes={self._max_archive_bytes}"
                )
            archive_data = src.read_bytes()
        else:
            archive_size = len(raw_bytes)
            if archive_size > self._max_archive_bytes:
                raise SourceAdapterError(
                    f"archive {filename!r} is {archive_size} bytes; "
                    f"exceeds max_archive_bytes={self._max_archive_bytes}"
                )
            archive_data = raw_bytes

        lower = filename.lower()
        if lower.endswith(".zip"):
            entries = self._extract_zip(archive_data, archive_size, filename)
        elif any(lower.endswith(ext) for ext in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
            entries = self._extract_tar(archive_data, archive_size, filename)
        else:
            raise SourceAdapterError(
                f"unsupported archive format: {filename!r} "
                "(expected .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz)"
            )

        if not entries:
            raise SourceAdapterError(
                f"archive {filename!r} contains no extractable files after filtering"
            )

        packages: list[IntakePackage] = []
        for member_name, payload in entries:
            pkg = self._build_package(member_name, payload, filename)
            packages.append(pkg)

        logger.info(
            "batch_adapter_enqueued",
            archive=filename,
            file_count=len(packages),
            archive_bytes=archive_size,
        )
        return packages

    # --- ZIP extraction ----------------------------------------------------

    def _extract_zip(
        self, data: bytes, archive_size: int, archive_name: str
    ) -> list[tuple[str, bytes]]:
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise SourceAdapterError(f"corrupt ZIP archive {archive_name!r}: {exc}") from exc

        with zf:
            infos = [
                i for i in zf.infolist() if not i.is_dir() and not _is_path_traversal(i.filename)
            ]

            traversal_skipped = [i for i in zf.infolist() if _is_path_traversal(i.filename)]
            for skipped in traversal_skipped:
                logger.warning(
                    "batch_adapter_path_traversal_skipped",
                    archive=archive_name,
                    member=skipped.filename,
                )

            infos = self._filter_members(infos, archive_name, key=lambda i: i.filename)

            if len(infos) > self._max_file_count:
                raise SourceAdapterError(
                    f"archive {archive_name!r} contains {len(infos)} files; "
                    f"exceeds max_file_count={self._max_file_count}"
                )

            uncompressed_total = sum(i.file_size for i in infos)
            if archive_size > 0:
                ratio = uncompressed_total / archive_size
                if ratio > self._max_compression_ratio:
                    raise SourceAdapterError(
                        f"archive {archive_name!r} compression ratio {ratio:.1f} "
                        f"exceeds max={self._max_compression_ratio} (zip-bomb guard)"
                    )

            entries: list[tuple[str, bytes]] = []
            for info in infos:
                try:
                    payload = zf.read(info.filename)
                except Exception as exc:
                    logger.warning(
                        "batch_adapter_member_read_failed",
                        archive=archive_name,
                        member=info.filename,
                        error=str(exc),
                    )
                    continue
                basename = Path(info.filename).name
                if basename:
                    entries.append((basename, payload))
            return entries

    # --- TAR extraction ----------------------------------------------------

    def _extract_tar(
        self, data: bytes, archive_size: int, archive_name: str
    ) -> list[tuple[str, bytes]]:
        try:
            tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")  # noqa: SIM115
        except (tarfile.TarError, EOFError) as exc:
            raise SourceAdapterError(f"corrupt tar archive {archive_name!r}: {exc}") from exc

        with tf:
            members = [
                m
                for m in tf.getmembers()
                if m.isfile() and not m.issym() and not m.islnk() and not _is_path_traversal(m.name)
            ]

            sym_skipped = [m for m in tf.getmembers() if m.issym() or m.islnk()]
            for skipped in sym_skipped:
                logger.warning(
                    "batch_adapter_symlink_skipped",
                    archive=archive_name,
                    member=skipped.name,
                )

            traversal_skipped = [
                m for m in tf.getmembers() if m.isfile() and _is_path_traversal(m.name)
            ]
            for skipped in traversal_skipped:
                logger.warning(
                    "batch_adapter_path_traversal_skipped",
                    archive=archive_name,
                    member=skipped.name,
                )

            members = self._filter_members(members, archive_name, key=lambda m: m.name)

            if len(members) > self._max_file_count:
                raise SourceAdapterError(
                    f"archive {archive_name!r} contains {len(members)} files; "
                    f"exceeds max_file_count={self._max_file_count}"
                )

            uncompressed_total = sum(m.size for m in members)
            if archive_size > 0:
                ratio = uncompressed_total / archive_size
                if ratio > self._max_compression_ratio:
                    raise SourceAdapterError(
                        f"archive {archive_name!r} compression ratio {ratio:.1f} "
                        f"exceeds max={self._max_compression_ratio} (zip-bomb guard)"
                    )

            entries: list[tuple[str, bytes]] = []
            for member in members:
                fobj = tf.extractfile(member)
                if fobj is None:
                    continue
                try:
                    payload = fobj.read()
                except Exception as exc:
                    logger.warning(
                        "batch_adapter_member_read_failed",
                        archive=archive_name,
                        member=member.name,
                        error=str(exc),
                    )
                    continue
                basename = Path(member.name).name
                if basename:
                    entries.append((basename, payload))
            return entries

    # --- Shared helpers -----------------------------------------------------

    def _filter_members(
        self,
        members: list,
        archive_name: str,
        *,
        key: Callable,
    ) -> list:
        import fnmatch

        filtered = []
        for m in members:
            name = Path(key(m)).name
            if not name:
                continue
            if any(fnmatch.fnmatch(name, pat) for pat in self._excluded_patterns):
                continue
            if not any(fnmatch.fnmatch(name, pat) for pat in self._glob_patterns):
                continue
            filtered.append(m)
        return filtered

    def _build_package(self, member_name: str, payload: bytes, archive_name: str) -> IntakePackage:
        size = len(payload)
        resolved_mime = self._mime_detect(payload, member_name)

        package_id = uuid4()
        safe = sanitize_filename(member_name)
        pkg_dir = self._storage_root / self._tenant_id / str(package_id)
        pkg_dir.mkdir(parents=True, exist_ok=True)
        dest = pkg_dir / safe
        dest.write_bytes(payload)

        intake_file = IntakeFile(
            file_path=str(dest),
            file_name=member_name,
            mime_type=resolved_mime,
            size_bytes=size,
            sha256=hashlib.sha256(payload).hexdigest(),
            sequence_index=0,
            source_metadata={
                "archive_name": archive_name,
                "original_member_path": member_name,
                "sanitized_filename": safe,
            },
        )

        pkg = IntakePackage(
            package_id=package_id,
            source_type=IntakeSourceType.BATCH_IMPORT,
            tenant_id=self._tenant_id,
            source_metadata={
                "archive_name": archive_name,
                "original_member_path": member_name,
                "mime_type": resolved_mime,
            },
            files=[intake_file],
        )

        self._queue.append(pkg)
        self._in_flight[package_id] = pkg
        return pkg

    # --- SourceAdapter contract ---------------------------------------------

    async def fetch_next(self) -> IntakePackage | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    async def acknowledge(self, package_id: UUID) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot acknowledge (not in-flight)"
            )
        self._in_flight.pop(package_id, None)
        logger.info("batch_adapter_acknowledged", package_id=str(package_id))

    async def reject(self, package_id: UUID, reason: str) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot reject (not in-flight)"
            )
        self._in_flight.pop(package_id, None)
        logger.info("batch_adapter_rejected", package_id=str(package_id), reason=reason)

    async def health_check(self) -> bool:
        try:
            self._storage_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        return os.access(self._storage_root, os.W_OK)
