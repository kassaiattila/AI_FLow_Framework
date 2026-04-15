"""EmailSourceAdapter — IMAP-backed source adapter producing IntakePackage.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N2,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 1 Day 2 — E1.1-A).

Pipeline per unseen message:
    IMAP UID → raw bytes → MIME parse → IntakePackage
        - subject + body        → IntakeDescription(role=EMAIL_BODY)
        - each MIME attachment  → IntakeFile (bytes spilled to storage_root)
    acknowledge(package_id)     → backend.mark_seen(uid)      (sets \\Seen)
    reject(package_id, reason)  → backend.mark_flagged(uid, reason)  (sets \\Flagged)

The backend is pluggable via `ImapBackendProtocol`; `ImapBackend` is the default
real implementation using stdlib `imaplib.IMAP4_SSL` wrapped with
`asyncio.to_thread` so the adapter stays fully async-safe.
"""

from __future__ import annotations

import asyncio
import email
import hashlib
import imaplib
from email.message import Message
from pathlib import Path
from typing import ClassVar, Protocol
from uuid import UUID

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

__all__ = [
    "EmailSourceAdapter",
    "ImapBackend",
    "ImapBackendProtocol",
]

logger = structlog.get_logger(__name__)


class ImapBackendProtocol(Protocol):
    """Minimal IMAP backend contract consumed by EmailSourceAdapter."""

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        """Return [(uid, raw_rfc822_bytes), ...] for every UNSEEN message."""
        ...

    async def mark_seen(self, uid: int) -> None:
        """Flag the message with the IMAP \\Seen flag."""
        ...

    async def mark_flagged(self, uid: int, reason: str) -> None:
        """Flag the message with the IMAP \\Flagged flag; `reason` is for logs."""
        ...

    async def ping(self) -> bool:
        """True if the backend can reach the IMAP server."""
        ...


class ImapBackend:
    """Real `imaplib.IMAP4_SSL` backend; synchronous calls are offloaded via `asyncio.to_thread`.

    One connection per operation — IMAP sessions are cheap and this keeps the
    backend stateless from the asyncio perspective.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 993,
        user: str,
        password: str,
        mailbox: str = "INBOX",
        use_ssl: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._mailbox = mailbox
        self._use_ssl = use_ssl

    def _connect(self) -> imaplib.IMAP4:
        conn: imaplib.IMAP4
        if self._use_ssl:
            conn = imaplib.IMAP4_SSL(self._host, self._port)
        else:
            conn = imaplib.IMAP4(self._host, self._port)
        conn.login(self._user, self._password)
        conn.select(self._mailbox)
        return conn

    def _fetch_unseen_sync(self) -> list[tuple[int, bytes]]:
        conn = self._connect()
        try:
            typ, data = conn.uid("search", None, "UNSEEN")  # type: ignore[arg-type]
            if typ != "OK" or not data or not data[0]:
                return []
            uids = [int(x) for x in data[0].split()]
            out: list[tuple[int, bytes]] = []
            for uid in uids:
                typ2, fetched = conn.uid("fetch", str(uid), "(BODY.PEEK[])")
                if typ2 != "OK" or not fetched:
                    continue
                for item in fetched:
                    if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
                        out.append((uid, item[1]))
                        break
            return out
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def _flag_sync(self, uid: int, flag: str) -> None:
        conn = self._connect()
        try:
            conn.uid("store", str(uid), "+FLAGS", f"({flag})")
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def _ping_sync(self) -> bool:
        try:
            conn = self._connect()
        except Exception:
            return False
        try:
            typ, _ = conn.noop()
            return typ == "OK"
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return await asyncio.to_thread(self._fetch_unseen_sync)

    async def mark_seen(self, uid: int) -> None:
        await asyncio.to_thread(self._flag_sync, uid, "\\Seen")

    async def mark_flagged(self, uid: int, reason: str) -> None:  # noqa: ARG002 - reason is for logs
        await asyncio.to_thread(self._flag_sync, uid, "\\Flagged")

    async def ping(self) -> bool:
        return await asyncio.to_thread(self._ping_sync)


def _decode_body_bytes(payload: bytes, charset: str | None) -> str:
    """Decode a text/* MIME payload; fall back to latin-1, then utf-8/replace."""
    for enc in (charset or "utf-8", "latin-1"):
        try:
            return payload.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return payload.decode("utf-8", errors="replace")


def _parse_mime(raw: bytes) -> tuple[Message, str, str, str, list[tuple[str, str, bytes]]]:
    """Parse raw RFC822 bytes → (msg, subject, from_, body_text, attachments).

    attachments is a list of (filename, mime_type, payload_bytes).
    """
    msg = email.message_from_bytes(raw)
    subject = str(msg.get("Subject", "") or "").strip()
    from_ = str(msg.get("From", "") or "").strip()

    body_parts: list[str] = []
    attachments: list[tuple[str, str, bytes]] = []

    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type() or "text/plain"
        disp = str(part.get("Content-Disposition", "") or "").lower()
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""

        is_attachment = "attachment" in disp or bool(filename)
        if is_attachment:
            attachments.append((filename or "attachment.bin", ctype, payload))
        elif ctype.startswith("text/"):
            body_parts.append(_decode_body_bytes(payload, part.get_content_charset()))

    body_text = "\n".join(p for p in body_parts if p).strip()
    return msg, subject, from_, body_text, attachments


class EmailSourceAdapter(SourceAdapter):
    """SourceAdapter that pulls unseen email messages via an IMAP backend.

    Constructor takes a backend implementing `ImapBackendProtocol` so that
    production code uses `ImapBackend` (real IMAP) while unit tests inject a
    fake. Attachment bytes are spilled to `storage_root/{tenant_id}/{package_id}/{file}`.
    """

    source_type: ClassVar[IntakeSourceType] = IntakeSourceType.EMAIL

    def __init__(
        self,
        *,
        backend: ImapBackendProtocol,
        storage_root: Path | str,
        tenant_id: str,
        max_package_bytes: int | None = None,
        adapter_name: str = "email_imap",
        adapter_version: str = "0.1.0",
    ) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        self._backend = backend
        self._storage_root = Path(storage_root)
        self._tenant_id = tenant_id
        self._max_package_bytes = max_package_bytes
        self._adapter_name = adapter_name
        self._adapter_version = adapter_version
        # Track in-flight packages so repeated fetch_next calls with the same
        # UID do not create duplicate IntakePackages before acknowledge().
        self._pending_uids: dict[int, UUID] = {}
        self._package_to_uid: dict[UUID, int] = {}

    @property
    def metadata(self) -> SourceAdapterMetadata:
        return SourceAdapterMetadata(
            name=self._adapter_name,
            version=self._adapter_version,
            source_type=IntakeSourceType.EMAIL,
            transport="pull",
            requires_ack=True,
            supports_batching=False,
            max_package_bytes=self._max_package_bytes,
        )

    async def fetch_next(self) -> IntakePackage | None:
        try:
            unseen = await self._backend.fetch_unseen()
        except Exception as exc:  # IMAP auth / network failure
            raise SourceAdapterError(f"IMAP fetch_unseen failed: {exc}") from exc

        for uid, raw in unseen:
            if uid in self._pending_uids:
                continue  # already in-flight, wait for ack/reject

            try:
                _msg, subject, from_, body_text, attachments = _parse_mime(raw)
            except Exception as exc:
                logger.warning("email_adapter_mime_parse_failed", uid=uid, error=str(exc))
                await self._backend.mark_flagged(uid, "mime_parse_error")
                continue

            total_bytes = sum(len(b) for _, _, b in attachments) + len(body_text.encode("utf-8"))
            if self._max_package_bytes is not None and total_bytes > self._max_package_bytes:
                logger.info(
                    "email_adapter_size_exceeded",
                    uid=uid,
                    total_bytes=total_bytes,
                    max_package_bytes=self._max_package_bytes,
                )
                await self._backend.mark_flagged(uid, "size_exceeded")
                continue

            pkg = self._build_package(
                uid=uid,
                subject=subject,
                from_=from_,
                body_text=body_text,
                attachments=attachments,
            )
            if pkg is None:
                # Truly empty message — no body, no attachments. Flag and skip.
                await self._backend.mark_flagged(uid, "empty_message")
                continue

            self._pending_uids[uid] = pkg.package_id
            self._package_to_uid[pkg.package_id] = uid
            logger.info(
                "email_adapter_fetched",
                uid=uid,
                package_id=str(pkg.package_id),
                files=len(pkg.files),
                descriptions=len(pkg.descriptions),
            )
            return pkg

        return None

    def _build_package(
        self,
        *,
        uid: int,
        subject: str,
        from_: str,
        body_text: str,
        attachments: list[tuple[str, str, bytes]],
    ) -> IntakePackage | None:
        # Pre-generate package_id so storage path is stable before construction.
        from uuid import uuid4

        package_id = uuid4()

        description_text_parts: list[str] = []
        if subject:
            description_text_parts.append(f"Subject: {subject}")
        if body_text:
            description_text_parts.append(body_text)
        description_text = "\n\n".join(description_text_parts).strip()

        descriptions: list[IntakeDescription] = []
        if description_text:
            descriptions.append(
                IntakeDescription(text=description_text, role=DescriptionRole.EMAIL_BODY)
            )

        files: list[IntakeFile] = []
        pkg_dir = self._storage_root / self._tenant_id / str(package_id)
        for index, (filename, mime_type, payload) in enumerate(attachments):
            safe = sanitize_filename(filename)
            pkg_dir.mkdir(parents=True, exist_ok=True)
            path = pkg_dir / safe
            path.write_bytes(payload)
            files.append(
                IntakeFile(
                    file_path=str(path),
                    file_name=filename or safe,
                    mime_type=mime_type or "application/octet-stream",
                    size_bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                    sequence_index=index,
                    source_metadata={"imap_uid": uid, "mime_type": mime_type},
                )
            )

        if not files and not descriptions:
            return None

        return IntakePackage(
            package_id=package_id,
            source_type=IntakeSourceType.EMAIL,
            tenant_id=self._tenant_id,
            source_metadata={
                "email_subject": subject,
                "email_from": from_,
                "imap_uid": uid,
            },
            files=files,
            descriptions=descriptions,
        )

    async def acknowledge(self, package_id: UUID) -> None:
        uid = self._package_to_uid.get(package_id)
        if uid is None:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot acknowledge (not in-flight)"
            )
        try:
            await self._backend.mark_seen(uid)
        except Exception as exc:
            raise SourceAdapterError(f"IMAP mark_seen failed for uid={uid}: {exc}") from exc
        self._pending_uids.pop(uid, None)
        self._package_to_uid.pop(package_id, None)
        logger.info("email_adapter_acknowledged", uid=uid, package_id=str(package_id))

    async def reject(self, package_id: UUID, reason: str) -> None:
        uid = self._package_to_uid.get(package_id)
        if uid is None:
            raise SourceAdapterError(
                f"Unknown package_id {package_id}; cannot reject (not in-flight)"
            )
        try:
            await self._backend.mark_flagged(uid, reason)
        except Exception as exc:
            raise SourceAdapterError(f"IMAP mark_flagged failed for uid={uid}: {exc}") from exc
        self._pending_uids.pop(uid, None)
        self._package_to_uid.pop(package_id, None)
        logger.info(
            "email_adapter_rejected",
            uid=uid,
            package_id=str(package_id),
            reason=reason,
        )

    async def health_check(self) -> bool:
        try:
            return await self._backend.ping()
        except Exception:
            return False
