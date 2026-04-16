"""FileSourceAdapter — push-mode single-file source adapter producing IntakePackage.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md R1,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 1 Day 4 — E1.3).

Unlike `EmailSourceAdapter` (pull), the file adapter is bridged from an
external uploader (REST endpoint `POST /api/v1/intake/upload-package`, CLI,
tests) via `enqueue(...)`. Each enqueue emits exactly one `IntakePackage`
with exactly one `IntakeFile`. Multi-file / description-bearing uploads
belong to the association layer (N4, E3.x) and are out of scope here.

`fetch_next` / `acknowledge` / `reject` still exist so the adapter satisfies
the same `SourceAdapter` contract as pull-mode adapters — registry- and
contract-test code treats them uniformly. `requires_ack=False` because there
is no upstream to flag back to; acknowledge is idempotent bookkeeping.
"""

from __future__ import annotations

import hashlib
import mimetypes
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar
from uuid import UUID, uuid4

import structlog

from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources._fs import sanitize_filename
from aiflow.sources.base import SourceAdapter, SourceAdapterMetadata
from aiflow.sources.exceptions import SourceAdapterError
from aiflow.sources.observability import emit_package_event

__all__ = [
    "FileSourceAdapter",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MIME = "application/octet-stream"


def _default_mime_detect(_payload: bytes, filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or _DEFAULT_MIME


class FileSourceAdapter(SourceAdapter):
    """Push-mode adapter: each enqueue() call yields one IntakePackage.

    Two input shapes are supported:
        * `raw_bytes=...` + `filename=...` — bytes streamed from an HTTP upload.
        * `file_path=...` — path on disk (e.g. CLI `aiflow intake upload ./x.pdf`).

    Collision policy: each package gets a fresh UUID → path is
    `storage_root/{tenant_id}/{package_id}/{sanitized_filename}`. Two uploads
    with the same filename therefore never overwrite each other.
    """

    source_type: ClassVar[IntakeSourceType] = IntakeSourceType.FILE_UPLOAD

    def __init__(
        self,
        *,
        storage_root: Path | str,
        tenant_id: str,
        max_package_bytes: int | None = None,
        mime_detect: Callable[[bytes, str], str] | None = None,
        adapter_name: str = "file_upload",
        adapter_version: str = "0.1.0",
    ) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        self._storage_root = Path(storage_root)
        self._tenant_id = tenant_id
        self._max_package_bytes = max_package_bytes
        self._mime_detect = mime_detect or _default_mime_detect
        self._adapter_name = adapter_name
        self._adapter_version = adapter_version
        self._queue: deque[IntakePackage] = deque()
        self._in_flight: dict[UUID, IntakePackage] = {}

    @property
    def metadata(self) -> SourceAdapterMetadata:
        return SourceAdapterMetadata(
            name=self._adapter_name,
            version=self._adapter_version,
            source_type=IntakeSourceType.FILE_UPLOAD,
            transport="push",
            requires_ack=False,
            supports_batching=False,
            max_package_bytes=self._max_package_bytes,
        )

    def enqueue(
        self,
        *,
        file_path: Path | str | None = None,
        raw_bytes: bytes | None = None,
        filename: str,
        mime_type: str | None = None,
        description: str | None = None,
    ) -> IntakePackage:
        """Bridge an external upload into the internal queue and return the package.

        Exactly one of `file_path` or `raw_bytes` must be provided. The returned
        IntakePackage is also appended to the queue so `fetch_next()` can drain
        it later (REST handlers typically use the return value directly and
        ignore the queue).
        """
        if not filename:
            raise ValueError("filename must be non-empty")
        if (file_path is None) == (raw_bytes is None):
            raise ValueError("exactly one of file_path or raw_bytes must be provided")

        if raw_bytes is None:
            assert file_path is not None  # narrowed by the xor check above
            payload = Path(file_path).read_bytes()
        else:
            payload = raw_bytes

        size = len(payload)
        if self._max_package_bytes is not None and size > self._max_package_bytes:
            logger.info(
                "file_adapter_size_exceeded",
                filename=filename,
                size_bytes=size,
                max_package_bytes=self._max_package_bytes,
            )
            raise SourceAdapterError(
                f"file upload {filename!r} is {size} bytes; exceeds max_package_bytes="
                f"{self._max_package_bytes}"
            )

        resolved_mime = mime_type or self._mime_detect(payload, filename)

        package_id = uuid4()
        safe = sanitize_filename(filename)
        pkg_dir = self._storage_root / self._tenant_id / str(package_id)
        pkg_dir.mkdir(parents=True, exist_ok=True)
        dest = pkg_dir / safe
        dest.write_bytes(payload)

        intake_file = IntakeFile(
            file_path=str(dest),
            file_name=filename,
            mime_type=resolved_mime,
            size_bytes=size,
            sha256=hashlib.sha256(payload).hexdigest(),
            sequence_index=0,
            source_metadata={"upload_filename": filename, "sanitized_filename": safe},
        )

        descriptions: list[IntakeDescription] = []
        if description and description.strip():
            descriptions.append(
                IntakeDescription(text=description.strip(), role=DescriptionRole.USER_NOTE)
            )

        pkg = IntakePackage(
            package_id=package_id,
            source_type=IntakeSourceType.FILE_UPLOAD,
            tenant_id=self._tenant_id,
            source_metadata={"upload_filename": filename, "mime_type": resolved_mime},
            files=[intake_file],
            descriptions=descriptions,
        )

        self._queue.append(pkg)
        self._in_flight[package_id] = pkg
        logger.info(
            "file_adapter_enqueued",
            package_id=str(package_id),
            filename=filename,
            size_bytes=size,
            mime_type=resolved_mime,
        )
        return pkg

    async def fetch_next(self) -> IntakePackage | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    async def acknowledge(self, package_id: UUID) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot acknowledge (not in-flight)"
            )
        pkg = self._in_flight.pop(package_id)
        logger.info("file_adapter_acknowledged", package_id=str(package_id))
        emit_package_event("source.package_received", pkg, source_type="file")

    async def reject(self, package_id: UUID, reason: str) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot reject (not in-flight)"
            )
        pkg = self._in_flight.pop(package_id)
        logger.info("file_adapter_rejected", package_id=str(package_id), reason=reason)
        emit_package_event("source.package_rejected", pkg, source_type="file", reason=reason)

    async def health_check(self) -> bool:
        try:
            self._storage_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        import os

        return os.access(self._storage_root, os.W_OK)
