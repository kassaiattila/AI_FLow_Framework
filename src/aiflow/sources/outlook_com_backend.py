"""OutlookComBackend — Windows-only Outlook COM backend for EmailSourceAdapter.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N2,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 1 Day 3 — E1.2-A).

Implements `ImapBackendProtocol` on top of the Outlook Object Model via
`win32com.client.Dispatch("Outlook.Application")`. Outlook uses `EntryID`
(hex string) as the stable message identifier; we hash each EntryID into a
stable positive int to satisfy the `(uid: int, raw: bytes)` protocol and keep
a two-way map so `mark_seen` / `mark_flagged` can resolve the original item.

COM objects are apartment-threaded. Every call runs via `asyncio.to_thread`
and each worker-thread invocation wraps its body in
`pythoncom.CoInitializeEx(COINIT_APARTMENTTHREADED)` / `CoUninitialize` so the
backend is safe to call from any event loop.

Outlook does not hand us RFC822 bytes directly, so `_item_to_mime_bytes`
synthesizes a minimal RFC822 message from the `MailItem` fields (Subject,
SenderEmailAddress, Body, Attachments). This is sufficient for the downstream
MIME parser in `EmailSourceAdapter` and keeps the code free of format quirks
between Outlook versions.

If `pywin32` is not importable (non-Windows, missing install), the backend
raises `SourceAdapterError` on construction with a clear fallback message;
callers can downgrade to `ImapBackend` or `GraphApiBackend`.
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol

import structlog

from aiflow.sources.exceptions import SourceAdapterError

__all__ = [
    "OutlookComBackend",
    "OutlookDispatchFactory",
]

logger = structlog.get_logger(__name__)

# Outlook Object Model constants (avoid importing pywin32 just for these).
_OL_FOLDER_INBOX = 6
_OL_FLAG_MARKED = 2
_OL_SAVE_AS_TYPE_MSG = 3


class OutlookDispatchFactory(Protocol):
    """Callable returning a COM Dispatch for 'Outlook.Application' (or a fake)."""

    def __call__(self, progid: str) -> Any: ...


def _default_dispatch_factory(progid: str) -> Any:
    """Lazy import so non-Windows environments fail only when actually used."""
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - platform guard
        raise SourceAdapterError(
            "pywin32 is required for OutlookComBackend; install pywin32 or "
            "choose ImapBackend / GraphApiBackend instead."
        ) from exc
    return win32com.client.Dispatch(progid)


def _entry_id_to_uid(entry_id: str) -> int:
    """Stable, positive 63-bit int derived from an Outlook EntryID hex string."""
    digest = hashlib.blake2b(entry_id.encode("ascii", errors="replace"), digest_size=8).digest()
    return int.from_bytes(digest, "big") & 0x7FFFFFFFFFFFFFFF


class OutlookComBackend:
    """`ImapBackendProtocol` implementation backed by the Outlook COM interface.

    Parameters
    ----------
    mailbox_folder:
        Name of a sub-folder under the default mailbox root to poll. Defaults
        to the Inbox via `olFolderInbox`.
    dispatch_factory:
        Override for `win32com.client.Dispatch` — lets tests inject a fake COM
        tree (see `tests/unit/sources/test_outlook_com_backend.py`).
    com_init:
        Callable invoked per worker-thread hop to initialize COM
        (`pythoncom.CoInitializeEx`). Default lazy-imports `pythoncom`.
    com_uninit:
        Paired `CoUninitialize` callable.
    """

    def __init__(
        self,
        *,
        mailbox_folder: str | None = None,
        dispatch_factory: OutlookDispatchFactory | None = None,
        com_init: Callable[[], None] | None = None,
        com_uninit: Callable[[], None] | None = None,
    ) -> None:
        self._mailbox_folder = mailbox_folder
        self._dispatch_factory = dispatch_factory or _default_dispatch_factory
        self._com_init = com_init or _default_com_init
        self._com_uninit = com_uninit or _default_com_uninit
        # EntryID ↔ stable uid maps
        self._uid_to_entry_id: dict[int, str] = {}

    # ---------------------------------------------------------------------
    # COM tree access helpers (sync — always called from a worker thread)
    # ---------------------------------------------------------------------

    def _get_inbox(self, app: Any) -> Any:
        namespace = app.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(_OL_FOLDER_INBOX)
        if self._mailbox_folder:
            inbox = inbox.Folders[self._mailbox_folder]
        return inbox

    def _iter_unread_items(self, inbox: Any) -> list[Any]:
        items = inbox.Items
        restricted = items.Restrict("[UnRead] = True")
        out: list[Any] = []
        for item in restricted:
            out.append(item)
        return out

    def _item_to_mime_bytes(self, item: Any) -> bytes:
        """Synthesize an RFC822 byte blob from a MailItem.

        Saving via Outlook's own `olMSG` format would require a temp file + a
        parser we do not own. Building an `EmailMessage` ourselves is simpler
        and produces exactly what `_parse_mime` in `email_adapter.py` expects.
        """
        msg = EmailMessage()
        subject = str(getattr(item, "Subject", "") or "")
        sender = str(getattr(item, "SenderEmailAddress", "") or "")
        to_ = str(getattr(item, "To", "") or "")
        body = str(getattr(item, "Body", "") or "")

        if subject:
            msg["Subject"] = subject
        if sender:
            msg["From"] = sender
        if to_:
            msg["To"] = to_
        msg.set_content(body or "", charset="utf-8")

        attachments = getattr(item, "Attachments", None)
        if attachments is not None:
            count = getattr(attachments, "Count", 0)
            # Outlook uses 1-based indexing.
            for idx in range(1, int(count) + 1):
                att = attachments.Item(idx) if hasattr(attachments, "Item") else attachments[idx]
                filename = str(getattr(att, "FileName", None) or f"attachment_{idx}.bin")
                payload = self._read_attachment_bytes(att, filename)
                if payload is None:
                    continue
                msg.add_attachment(
                    payload,
                    maintype="application",
                    subtype="octet-stream",
                    filename=filename,
                )
        return msg.as_bytes()

    def _read_attachment_bytes(self, attachment: Any, filename: str) -> bytes | None:
        """Prefer in-memory bytes; fall back to `SaveAsFile` + read."""
        for attr in ("GetBytes", "Bytes", "Data"):
            provider = getattr(attachment, attr, None)
            if provider is None:
                continue
            try:
                data = provider() if callable(provider) else provider
            except Exception:  # pragma: no cover - defensive
                continue
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        save = getattr(attachment, "SaveAsFile", None)
        if callable(save):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / filename
                try:
                    save(str(path))
                    return path.read_bytes()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(
                        "outlook_com_attachment_read_failed",
                        filename=filename,
                        error=str(exc),
                    )
                    return None
        return None

    # ---------------------------------------------------------------------
    # Sync operations (invoked via asyncio.to_thread)
    # ---------------------------------------------------------------------

    def _fetch_unseen_sync(self) -> list[tuple[int, bytes]]:
        self._com_init()
        try:
            app = self._dispatch_factory("Outlook.Application")
            inbox = self._get_inbox(app)
            out: list[tuple[int, bytes]] = []
            for item in self._iter_unread_items(inbox):
                entry_id = str(getattr(item, "EntryID", "") or "")
                if not entry_id:
                    continue
                uid = _entry_id_to_uid(entry_id)
                self._uid_to_entry_id[uid] = entry_id
                raw = self._item_to_mime_bytes(item)
                out.append((uid, raw))
            return out
        finally:
            self._com_uninit()

    def _find_item_by_uid_sync(self, app: Any, uid: int) -> Any | None:
        entry_id = self._uid_to_entry_id.get(uid)
        if entry_id is None:
            return None
        namespace = app.GetNamespace("MAPI")
        try:
            return namespace.GetItemFromID(entry_id)
        except Exception:
            return None

    def _mark_seen_sync(self, uid: int) -> None:
        self._com_init()
        try:
            app = self._dispatch_factory("Outlook.Application")
            item = self._find_item_by_uid_sync(app, uid)
            if item is None:
                raise SourceAdapterError(
                    f"Outlook item not found for uid={uid} (EntryID lost or deleted)"
                )
            item.UnRead = False
            item.Save()
        finally:
            self._com_uninit()

    def _mark_flagged_sync(self, uid: int, reason: str) -> None:
        self._com_init()
        try:
            app = self._dispatch_factory("Outlook.Application")
            item = self._find_item_by_uid_sync(app, uid)
            if item is None:
                raise SourceAdapterError(
                    f"Outlook item not found for uid={uid} (EntryID lost or deleted)"
                )
            # Outlook's FlagStatus = olFlagMarked; categories carry audit reason.
            item.FlagStatus = _OL_FLAG_MARKED
            existing = str(getattr(item, "Categories", "") or "").strip()
            tag = f"aiflow:{reason}"
            if existing:
                if tag not in {c.strip() for c in existing.split(",")}:
                    item.Categories = f"{existing}, {tag}"
            else:
                item.Categories = tag
            item.Save()
        finally:
            self._com_uninit()

    def _ping_sync(self) -> bool:
        self._com_init()
        try:
            app = self._dispatch_factory("Outlook.Application")
            namespace = app.GetNamespace("MAPI")
            accounts = getattr(namespace, "Accounts", None)
            if accounts is None:
                return False
            return int(getattr(accounts, "Count", 0)) > 0
        except Exception:
            return False
        finally:
            self._com_uninit()

    # ---------------------------------------------------------------------
    # ImapBackendProtocol (async) surface
    # ---------------------------------------------------------------------

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return await asyncio.to_thread(self._fetch_unseen_sync)

    async def mark_seen(self, uid: int) -> None:
        await asyncio.to_thread(self._mark_seen_sync, uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        await asyncio.to_thread(self._mark_flagged_sync, uid, reason)

    async def ping(self) -> bool:
        return await asyncio.to_thread(self._ping_sync)


def _default_com_init() -> None:
    try:
        import pythoncom  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - platform guard
        return
    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    except Exception:
        # COM already initialised on this thread — safe to ignore.
        pass


def _default_com_uninit() -> None:
    try:
        import pythoncom  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - platform guard
        return
    try:
        pythoncom.CoUninitialize()
    except Exception:
        pass
