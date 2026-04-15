"""Unit tests for OutlookComBackend (Phase 1b — Week 1 Day 3 — E1.2-A).

A fake Outlook COM object tree is injected via `dispatch_factory` so the tests
run on any platform without pywin32 / a live Outlook instance.

The Fake*** classes below mirror the Outlook COM API which uses PascalCase
method names; `ruff: noqa: N802` keeps the mirror faithful.

@test_registry: unit/sources/outlook_com_backend
"""
# ruff: noqa: N802

from __future__ import annotations

import email
from typing import Any

import pytest

from aiflow.sources import OutlookComBackend, SourceAdapterError
from aiflow.sources.outlook_com_backend import _entry_id_to_uid

# ---------------------------------------------------------------------------
# Fake Outlook COM object tree
# ---------------------------------------------------------------------------


class FakeAttachment:
    def __init__(self, filename: str, data: bytes) -> None:
        self.FileName = filename
        self._data = data

    def GetBytes(self) -> bytes:
        return self._data


class FakeAttachments:
    def __init__(self, items: list[FakeAttachment]) -> None:
        self._items = items
        self.Count = len(items)

    def Item(self, index: int) -> FakeAttachment:
        # Outlook uses 1-based indexing.
        return self._items[index - 1]


class FakeMailItem:
    def __init__(
        self,
        *,
        entry_id: str,
        subject: str = "",
        sender: str = "",
        to: str = "",
        body: str = "",
        attachments: list[FakeAttachment] | None = None,
        unread: bool = True,
    ) -> None:
        self.EntryID = entry_id
        self.Subject = subject
        self.SenderEmailAddress = sender
        self.To = to
        self.Body = body
        self.Attachments = FakeAttachments(attachments or [])
        self.UnRead = unread
        self.FlagStatus = 0
        self.Categories = ""
        self.save_count = 0

    def Save(self) -> None:
        self.save_count += 1


class FakeItems:
    def __init__(self, items: list[FakeMailItem]) -> None:
        self._items = items

    def Restrict(self, query: str) -> list[FakeMailItem]:
        if query.strip().lower() == "[unread] = true":
            return [i for i in self._items if i.UnRead]
        return list(self._items)


class FakeFolder:
    def __init__(self, items: list[FakeMailItem]) -> None:
        self.Items = FakeItems(items)
        self.Folders: dict[str, FakeFolder] = {}


class FakeAccounts:
    def __init__(self, count: int) -> None:
        self.Count = count


class FakeNamespace:
    def __init__(
        self,
        *,
        inbox: FakeFolder,
        items_by_entry_id: dict[str, FakeMailItem],
        accounts_count: int = 1,
        raise_on_get_item: bool = False,
    ) -> None:
        self._inbox = inbox
        self._items_by_entry_id = items_by_entry_id
        self.Accounts = FakeAccounts(accounts_count)
        self._raise_on_get_item = raise_on_get_item

    def GetDefaultFolder(self, folder_id: int) -> FakeFolder:
        assert folder_id == 6, f"unexpected folder id {folder_id}"
        return self._inbox

    def GetItemFromID(self, entry_id: str) -> FakeMailItem:
        if self._raise_on_get_item:
            raise RuntimeError("COM: item not found")
        if entry_id not in self._items_by_entry_id:
            raise RuntimeError(f"unknown entry id {entry_id}")
        return self._items_by_entry_id[entry_id]


class FakeOutlookApp:
    def __init__(self, namespace: FakeNamespace) -> None:
        self._namespace = namespace

    def GetNamespace(self, name: str) -> FakeNamespace:
        assert name == "MAPI"
        return self._namespace


def _build_app(
    items: list[FakeMailItem],
    *,
    accounts_count: int = 1,
    raise_on_get_item: bool = False,
) -> FakeOutlookApp:
    inbox = FakeFolder(items)
    ns = FakeNamespace(
        inbox=inbox,
        items_by_entry_id={i.EntryID: i for i in items},
        accounts_count=accounts_count,
        raise_on_get_item=raise_on_get_item,
    )
    return FakeOutlookApp(ns)


def _make_backend(app: FakeOutlookApp) -> OutlookComBackend:
    return OutlookComBackend(
        dispatch_factory=lambda progid: app,
        com_init=lambda: None,
        com_uninit=lambda: None,
    )


# ---------------------------------------------------------------------------
# 1. fetch_unseen on an empty inbox returns []
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_unseen_empty_inbox() -> None:
    app = _build_app([])
    backend = _make_backend(app)
    assert await backend.fetch_unseen() == []


# ---------------------------------------------------------------------------
# 2. fetch_unseen skips already-read items (Restrict("[UnRead] = True"))
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_unseen_skips_read_items() -> None:
    items = [
        FakeMailItem(entry_id="A1", subject="read one", unread=False),
        FakeMailItem(entry_id="B2", subject="unread one", unread=True),
    ]
    backend = _make_backend(_build_app(items))
    out = await backend.fetch_unseen()
    assert len(out) == 1
    _, raw = out[0]
    assert b"unread one" in raw


# ---------------------------------------------------------------------------
# 3. EntryID → stable deterministic uid (repeated calls produce same uid)
# ---------------------------------------------------------------------------


def test_entry_id_to_uid_is_stable() -> None:
    uid_a = _entry_id_to_uid("0000000082A4F3")
    uid_b = _entry_id_to_uid("0000000082A4F3")
    uid_c = _entry_id_to_uid("AAAAAAAAAAAAAAA")
    assert uid_a == uid_b
    assert uid_a != uid_c
    assert 0 <= uid_a < 2**63  # positive 63-bit


# ---------------------------------------------------------------------------
# 4. MIME synthesis: subject + body + from parsed round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mime_synthesis_includes_subject_body_from() -> None:
    item = FakeMailItem(
        entry_id="E1",
        subject="Hello",
        sender="alice@example.com",
        to="bob@example.com",
        body="Body goes here.",
    )
    backend = _make_backend(_build_app([item]))
    out = await backend.fetch_unseen()
    assert len(out) == 1
    _, raw = out[0]
    msg = email.message_from_bytes(raw)
    assert msg["Subject"] == "Hello"
    assert msg["From"] == "alice@example.com"
    assert msg["To"] == "bob@example.com"
    # Without attachments the MIME blob is a single text/plain part.
    body_payload = msg.get_payload(decode=True)
    assert b"Body goes here." in body_payload


# ---------------------------------------------------------------------------
# 5. Attachment bytes survive through MIME synthesis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attachments_are_embedded_in_mime() -> None:
    pdf = b"%PDF-1.4 fake"
    item = FakeMailItem(
        entry_id="E2",
        subject="with file",
        body="see attached",
        attachments=[FakeAttachment("invoice.pdf", pdf)],
    )
    backend = _make_backend(_build_app([item]))
    out = await backend.fetch_unseen()
    _, raw = out[0]
    msg = email.message_from_bytes(raw)
    attach_parts = [p for p in msg.walk() if p.get_filename()]
    assert len(attach_parts) == 1
    assert attach_parts[0].get_filename() == "invoice.pdf"
    assert attach_parts[0].get_payload(decode=True) == pdf


# ---------------------------------------------------------------------------
# 6. fetch_unseen populates uid_to_entry_id map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_unseen_records_entry_id_mapping() -> None:
    item = FakeMailItem(entry_id="MAP-ME", subject="x", body="y")
    backend = _make_backend(_build_app([item]))
    out = await backend.fetch_unseen()
    uid, _ = out[0]
    assert backend._uid_to_entry_id[uid] == "MAP-ME"


# ---------------------------------------------------------------------------
# 7. mark_seen flips UnRead=False and Saves
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_seen_sets_unread_false_and_saves() -> None:
    item = FakeMailItem(entry_id="S1", subject="s", body="b")
    app = _build_app([item])
    backend = _make_backend(app)
    out = await backend.fetch_unseen()
    uid, _ = out[0]
    await backend.mark_seen(uid)
    assert item.UnRead is False
    assert item.save_count == 1


# ---------------------------------------------------------------------------
# 8. mark_flagged sets FlagStatus=olFlagMarked + category + saves
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_flagged_sets_flag_and_category() -> None:
    item = FakeMailItem(entry_id="F1", subject="s", body="b")
    backend = _make_backend(_build_app([item]))
    out = await backend.fetch_unseen()
    uid, _ = out[0]
    await backend.mark_flagged(uid, "size_exceeded")
    assert item.FlagStatus == 2  # olFlagMarked
    assert item.Categories == "aiflow:size_exceeded"
    assert item.save_count == 1


# ---------------------------------------------------------------------------
# 9. mark_flagged preserves existing categories and de-dupes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_flagged_preserves_and_dedupes_categories() -> None:
    item = FakeMailItem(entry_id="F2", subject="s", body="b")
    item.Categories = "ManualReview"
    backend = _make_backend(_build_app([item]))
    out = await backend.fetch_unseen()
    uid, _ = out[0]
    await backend.mark_flagged(uid, "policy_violation")
    assert "ManualReview" in item.Categories
    assert "aiflow:policy_violation" in item.Categories
    # Re-flagging with the same reason must not duplicate.
    await backend.mark_flagged(uid, "policy_violation")
    assert item.Categories.count("aiflow:policy_violation") == 1


# ---------------------------------------------------------------------------
# 10. mark_seen with unknown uid raises SourceAdapterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_seen_unknown_uid_raises() -> None:
    backend = _make_backend(_build_app([]))
    with pytest.raises(SourceAdapterError, match="Outlook item not found"):
        await backend.mark_seen(12345)


# ---------------------------------------------------------------------------
# 11. mark_flagged with unknown uid raises SourceAdapterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_flagged_unknown_uid_raises() -> None:
    backend = _make_backend(_build_app([]))
    with pytest.raises(SourceAdapterError, match="Outlook item not found"):
        await backend.mark_flagged(99999, "policy")


# ---------------------------------------------------------------------------
# 12. ping returns True when the MAPI session has >=1 account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ping_returns_true_when_account_present() -> None:
    backend = _make_backend(_build_app([], accounts_count=1))
    assert await backend.ping() is True


# ---------------------------------------------------------------------------
# 13. ping returns False when no accounts configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ping_returns_false_without_accounts() -> None:
    backend = _make_backend(_build_app([], accounts_count=0))
    assert await backend.ping() is False


# ---------------------------------------------------------------------------
# 14. ping returns False when Dispatch itself raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ping_returns_false_on_dispatch_failure() -> None:
    def failing_dispatch(_progid: str) -> Any:
        raise RuntimeError("COM server unreachable")

    backend = OutlookComBackend(
        dispatch_factory=failing_dispatch,
        com_init=lambda: None,
        com_uninit=lambda: None,
    )
    assert await backend.ping() is False


# ---------------------------------------------------------------------------
# 15. com_init / com_uninit are invoked once per call, paired
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_com_init_and_uninit_are_paired_per_call() -> None:
    init_calls: list[int] = []
    uninit_calls: list[int] = []

    def track_init() -> None:
        init_calls.append(1)

    def track_uninit() -> None:
        uninit_calls.append(1)

    item = FakeMailItem(entry_id="C1", subject="s", body="b")
    app = _build_app([item])
    backend = OutlookComBackend(
        dispatch_factory=lambda progid: app,
        com_init=track_init,
        com_uninit=track_uninit,
    )
    out = await backend.fetch_unseen()
    uid, _ = out[0]
    await backend.mark_seen(uid)
    await backend.ping()
    # fetch_unseen + mark_seen + ping = 3 paired init/uninit cycles.
    assert len(init_calls) == 3
    assert len(uninit_calls) == 3


# ---------------------------------------------------------------------------
# 16. Item without EntryID is silently skipped (defensive)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_item_without_entry_id_is_skipped() -> None:
    item = FakeMailItem(entry_id="", subject="ghost", body="no id")
    backend = _make_backend(_build_app([item]))
    assert await backend.fetch_unseen() == []
