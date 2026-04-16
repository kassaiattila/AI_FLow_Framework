"""Integration tests — EmailSourceAdapter wired with OutlookComBackend.

Validates that OutlookComBackend satisfies ImapBackendProtocol end-to-end: the
adapter builds an IntakePackage from the synthesized MIME bytes, acknowledge
marks the Outlook item read, and reject flags it with an audit category.

@test_registry: unit/sources/email_adapter_outlook
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.intake.package import IntakePackage, IntakeSourceType
from aiflow.sources import EmailSourceAdapter, OutlookComBackend
from tests.unit.sources.test_outlook_com_backend import (
    FakeAttachment,
    FakeMailItem,
    _build_app,
)


def _make_backend(app) -> OutlookComBackend:
    return OutlookComBackend(
        dispatch_factory=lambda progid: app,
        com_init=lambda: None,
        com_uninit=lambda: None,
    )


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


# ---------------------------------------------------------------------------
# 1. fetch_next via OutlookComBackend → IntakePackage with body + attachment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_next_via_outlook_backend_builds_intake_package(
    storage_root: Path,
) -> None:
    pdf = b"%PDF-1.4 outlook-com-bytes"
    item = FakeMailItem(
        entry_id="ENTRY-001",
        subject="Quarterly report",
        sender="ceo@example.com",
        to="me@example.com",
        body="Please review the attached report.",
        attachments=[FakeAttachment("Q1.pdf", pdf)],
    )
    backend = _make_backend(_build_app([item]))
    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id="tenant_a",
    )

    pkg = await adapter.fetch_next()

    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.EMAIL
    assert pkg.source_metadata["email_subject"] == "Quarterly report"
    assert len(pkg.files) == 1
    assert pkg.files[0].file_name == "Q1.pdf"
    assert Path(pkg.files[0].file_path).read_bytes() == pdf
    assert len(pkg.descriptions) == 1
    assert "Please review the attached report." in pkg.descriptions[0].text


# ---------------------------------------------------------------------------
# 2. acknowledge → Outlook item UnRead=False + Saved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_marks_outlook_item_read(storage_root: Path) -> None:
    item = FakeMailItem(
        entry_id="ENTRY-002",
        subject="hi",
        sender="a@x",
        body="body",
    )
    backend = _make_backend(_build_app([item]))
    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id="tenant_a",
    )

    pkg = await adapter.fetch_next()
    assert pkg is not None
    await adapter.acknowledge(pkg.package_id)

    assert item.UnRead is False
    assert item.save_count >= 1


# ---------------------------------------------------------------------------
# 3. reject → Outlook FlagStatus + audit category via Categories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_flags_outlook_item_with_audit_category(
    storage_root: Path,
) -> None:
    item = FakeMailItem(
        entry_id="ENTRY-003",
        subject="big mail",
        sender="a@x",
        body="body",
    )
    backend = _make_backend(_build_app([item]))
    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id="tenant_a",
    )

    pkg = await adapter.fetch_next()
    assert pkg is not None
    await adapter.reject(pkg.package_id, reason="policy_violation")

    assert item.FlagStatus == 2  # olFlagMarked
    assert "aiflow:policy_violation" in item.Categories


# ---------------------------------------------------------------------------
# 4. size_exceeded auto-reject path uses OutlookComBackend.mark_flagged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_size_guard_auto_flags_outlook_item(storage_root: Path) -> None:
    huge = b"X" * 20_000
    item = FakeMailItem(
        entry_id="ENTRY-004",
        subject="huge",
        body="huge",
        attachments=[FakeAttachment("big.bin", huge)],
    )
    backend = _make_backend(_build_app([item]))
    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id="tenant_a",
        max_package_bytes=1024,
    )

    assert await adapter.fetch_next() is None
    assert item.FlagStatus == 2
    assert "aiflow:size_exceeded" in item.Categories
