"""ApiSourceAdapter — push-mode webhook source with HMAC signature verification.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md R1,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 2 Day 8 — E2.3-A).

Unlike ``FileSourceAdapter``, this adapter is fed by external webhook callers
that authenticate each payload with a shared HMAC secret. The FastAPI router
that accepts ``POST /api/v1/sources/webhook`` (E2.3-B, Day 9) forwards the raw
body plus the signature / timestamp / idempotency headers to ``enqueue()``.

Security invariants enforced here (the router MUST NOT skip any):
* **HMAC-SHA256 verification** — timing-safe via ``hmac.compare_digest``.
* **Replay window** — ``abs(now - timestamp) > max_clock_skew_seconds`` → reject.
* **Idempotency** — a previously-seen key raises ``SourceAdapterError``; the
  router should translate that to HTTP 409.
* **Secret never leaves this module** — not logged, not in exception messages.

Out of scope for E2.3-A: FastAPI router wiring, rate limiting, persistent
idempotency store (in-memory dict is sufficient for the adapter contract).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
import time
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
from aiflow.sources.observability import emit_package_event

__all__ = [
    "ApiSourceAdapter",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MIME = "application/octet-stream"
_DEFAULT_MAX_CLOCK_SKEW_SECONDS = 300


def _default_mime_detect(_payload: bytes, filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or _DEFAULT_MIME


def _compute_signature(secret: bytes, timestamp: str, payload: bytes) -> str:
    """Compute the expected HMAC-SHA256 signature as hex.

    Signed string layout: ``<timestamp>.<base64(payload)>``. The timestamp is
    inside the signed envelope so the replay window check is bound to the
    signature — an attacker cannot reuse a signature under a fresher timestamp.
    """
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


class ApiSourceAdapter(SourceAdapter):
    """Push-mode webhook adapter: ``enqueue()`` verifies HMAC + replay window.

    Each accepted webhook yields one ``IntakePackage`` containing exactly one
    ``IntakeFile`` — multi-file webhook payloads are out of scope (they belong
    to ``BatchSourceAdapter`` via an archive upload).

    Storage layout mirrors ``FileSourceAdapter``:
    ``storage_root/{tenant}/{package_id}/{sanitized_filename}``.
    """

    source_type: ClassVar[IntakeSourceType] = IntakeSourceType.API_PUSH

    def __init__(
        self,
        *,
        storage_root: Path | str,
        tenant_id: str,
        hmac_secret: str | bytes,
        signature_header: str = "X-Webhook-Signature",
        timestamp_header: str = "X-Webhook-Timestamp",
        max_clock_skew_seconds: int = _DEFAULT_MAX_CLOCK_SKEW_SECONDS,
        max_package_bytes: int | None = None,
        mime_detect: Callable[[bytes, str], str] | None = None,
        adapter_name: str = "api_push",
        adapter_version: str = "0.1.0",
        now: Callable[[], int] | None = None,
    ) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        if not hmac_secret:
            raise ValueError("hmac_secret must be non-empty")
        if max_clock_skew_seconds <= 0:
            raise ValueError("max_clock_skew_seconds must be > 0")
        self._storage_root = Path(storage_root)
        self._tenant_id = tenant_id
        self._secret = hmac_secret.encode("utf-8") if isinstance(hmac_secret, str) else hmac_secret
        self._signature_header = signature_header
        self._timestamp_header = timestamp_header
        self._max_clock_skew_seconds = max_clock_skew_seconds
        self._max_package_bytes = max_package_bytes
        self._mime_detect = mime_detect or _default_mime_detect
        self._adapter_name = adapter_name
        self._adapter_version = adapter_version
        self._now = now or (lambda: int(time.time()))
        self._queue: deque[IntakePackage] = deque()
        self._in_flight: dict[UUID, IntakePackage] = {}
        self._seen_idempotency_keys: set[str] = set()

    @property
    def metadata(self) -> SourceAdapterMetadata:
        return SourceAdapterMetadata(
            name=self._adapter_name,
            version=self._adapter_version,
            source_type=IntakeSourceType.API_PUSH,
            transport="push",
            requires_ack=False,
            supports_batching=False,
            max_package_bytes=self._max_package_bytes,
        )

    def enqueue(
        self,
        *,
        payload: bytes,
        filename: str,
        signature: str,
        timestamp: str,
        idempotency_key: str | None = None,
        mime_type: str | None = None,
    ) -> IntakePackage:
        """Verify the webhook envelope and emit one ``IntakePackage``.

        Ordering of checks matches the cheapest-first principle: shape
        validation, size guard, replay window, HMAC verify, idempotency.
        HMAC verification happens *before* idempotency because a forged
        request must not be able to poison the seen-keys set.
        """
        if not filename:
            raise ValueError("filename must be non-empty")
        if not signature:
            raise SourceAdapterError("missing signature")
        if not timestamp:
            raise SourceAdapterError("missing timestamp")

        size = len(payload)
        if self._max_package_bytes is not None and size > self._max_package_bytes:
            logger.info(
                "api_adapter_size_exceeded",
                filename=filename,
                size_bytes=size,
                max_package_bytes=self._max_package_bytes,
            )
            raise SourceAdapterError(
                f"webhook payload {filename!r} is {size} bytes; "
                f"exceeds max_package_bytes={self._max_package_bytes}"
            )

        try:
            ts_int = int(timestamp)
        except ValueError as exc:
            raise SourceAdapterError(f"invalid timestamp: {timestamp!r}") from exc

        now_int = self._now()
        if abs(now_int - ts_int) > self._max_clock_skew_seconds:
            logger.info(
                "api_adapter_replay_window_exceeded",
                filename=filename,
                clock_skew_seconds=abs(now_int - ts_int),
                max_clock_skew_seconds=self._max_clock_skew_seconds,
            )
            raise SourceAdapterError(
                "timestamp outside replay window "
                f"(skew={abs(now_int - ts_int)}s, max={self._max_clock_skew_seconds}s)"
            )

        expected = _compute_signature(self._secret, timestamp, payload)
        if not hmac.compare_digest(expected, signature):
            logger.info(
                "api_adapter_invalid_signature",
                filename=filename,
                size_bytes=size,
            )
            raise SourceAdapterError("invalid HMAC signature")

        if idempotency_key is not None:
            if idempotency_key in self._seen_idempotency_keys:
                logger.info(
                    "api_adapter_duplicate_idempotency_key",
                    filename=filename,
                    idempotency_key=idempotency_key,
                )
                raise SourceAdapterError(f"duplicate idempotency_key={idempotency_key!r}")
            self._seen_idempotency_keys.add(idempotency_key)

        resolved_mime = mime_type or self._mime_detect(payload, filename)

        package_id = uuid4()
        safe = sanitize_filename(filename)
        pkg_dir = self._storage_root / self._tenant_id / str(package_id)
        pkg_dir.mkdir(parents=True, exist_ok=True)
        dest = pkg_dir / safe
        dest.write_bytes(payload)

        file_metadata: dict[str, object] = {
            "upload_filename": filename,
            "sanitized_filename": safe,
            "webhook_timestamp": ts_int,
        }
        if idempotency_key is not None:
            file_metadata["idempotency_key"] = idempotency_key

        intake_file = IntakeFile(
            file_path=str(dest),
            file_name=filename,
            mime_type=resolved_mime,
            size_bytes=size,
            sha256=hashlib.sha256(payload).hexdigest(),
            sequence_index=0,
            source_metadata=file_metadata,
        )

        package_source_metadata: dict[str, object] = {
            "upload_filename": filename,
            "mime_type": resolved_mime,
            "webhook_timestamp": ts_int,
        }
        if idempotency_key is not None:
            package_source_metadata["idempotency_key"] = idempotency_key

        pkg = IntakePackage(
            package_id=package_id,
            source_type=IntakeSourceType.API_PUSH,
            tenant_id=self._tenant_id,
            source_metadata=package_source_metadata,
            files=[intake_file],
        )

        self._queue.append(pkg)
        self._in_flight[package_id] = pkg
        logger.info(
            "api_adapter_enqueued",
            package_id=str(package_id),
            filename=filename,
            size_bytes=size,
            mime_type=resolved_mime,
            has_idempotency_key=idempotency_key is not None,
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
        logger.info("api_adapter_acknowledged", package_id=str(package_id))
        emit_package_event("source.package_received", pkg, source_type="api")

    async def reject(self, package_id: UUID, reason: str) -> None:
        if package_id not in self._in_flight:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot reject (not in-flight)"
            )
        pkg = self._in_flight.pop(package_id)
        logger.info("api_adapter_rejected", package_id=str(package_id), reason=reason)
        emit_package_event("source.package_rejected", pkg, source_type="api", reason=reason)

    async def health_check(self) -> bool:
        try:
            self._storage_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        import os

        return os.access(self._storage_root, os.W_OK)
