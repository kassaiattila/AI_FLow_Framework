"""E2E — EmailSourceAdapter (Week 1 Day 5 / E1.4).

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, intake, source_adapter, email]

Real pipeline (except IMAP wire): EmailSourceAdapter + FakeImapBackend reused
from tests/unit/sources/test_email_adapter.py. Payloads spill to the real
tmp storage_root; backend tracks \\Seen / \\Flagged against real dict state.
Real IMAP round-trips (Outlook COM or Docker MailDev) are scoped to Week 2
hardening — see session_S55 Day 5 guidance and 101 N2.

DB persistence round-trip is intentionally NOT exercised here: per
feedback_asyncpg_pool_event_loop.md the module-level asyncpg pool is bound
to the first event loop, so multiple function-scoped async tests reaching
for the pool crash with InterfaceError. Real-DB contract lives in
test_alembic_034.py (single merged method).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import DescriptionRole, IntakeSourceType
from aiflow.sources import EmailSourceAdapter, SourceAdapterError
from aiflow.sources.registry import SourceAdapterRegistry

# Reuse the fake + MIME builders instead of duplicating them per session_S60 STOP rule.
from tests.unit.sources.test_email_adapter import (
    FakeImapBackend,
    _make_multipart_with_attachments,
)


@pytest.mark.asyncio
async def test_email_source_happy_path(
    phase_1b_storage_root: Path,
    phase_1b_source_registry: SourceAdapterRegistry,
) -> None:
    """Two multipart messages → two IntakePackages persisted → acknowledge marks \\Seen."""
    tenant_id = f"tenant-e2e-email-happy-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / "email_happy"

    pdf_bytes = b"%PDF-1.4 invoice-e2e dummy\n"
    csv_bytes = b"col_a,col_b\n1,2\n3,4\n"
    txt_bytes = b"contract terms attached as text\n"

    msg_invoices = _make_multipart_with_attachments(
        subject="Two invoices",
        sender="biller@example.com",
        body="Please find the two invoices attached.",
        attachments=[
            ("invoice-a.pdf", "application/pdf", pdf_bytes),
            ("ledger.csv", "text/csv", csv_bytes),
        ],
    )
    msg_contract = _make_multipart_with_attachments(
        subject="Signed contract",
        sender="legal@example.com",
        body="See attached signed contract draft.",
        attachments=[
            ("contract.pdf", "application/pdf", pdf_bytes + b"contract-marker"),
            ("notes.txt", "text/plain", txt_bytes),
        ],
    )
    backend = FakeImapBackend([(1001, msg_invoices), (1002, msg_contract)])

    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id=tenant_id,
    )
    phase_1b_source_registry.register(EmailSourceAdapter)
    assert phase_1b_source_registry.has(IntakeSourceType.EMAIL)

    pkg_first = await adapter.fetch_next()
    assert pkg_first is not None
    assert pkg_first.source_type == IntakeSourceType.EMAIL
    assert len(pkg_first.files) == 2
    assert len(pkg_first.descriptions) == 1
    assert pkg_first.descriptions[0].role == DescriptionRole.EMAIL_BODY

    pkg_second = await adapter.fetch_next()
    assert pkg_second is not None
    assert pkg_second.package_id != pkg_first.package_id
    assert len(pkg_second.files) == 2

    assert await adapter.fetch_next() is None, "third fetch must not produce duplicates"

    for pkg in (pkg_first, pkg_second):
        for f in pkg.files:
            on_disk = Path(f.file_path)
            assert on_disk.exists()
            assert on_disk.is_relative_to(storage_root / tenant_id / str(pkg.package_id))
            assert on_disk.stat().st_size == f.size_bytes

    assert {f.file_name for f in pkg_first.files} == {"invoice-a.pdf", "ledger.csv"}
    assert pkg_first.source_metadata["imap_uid"] == 1001
    assert pkg_second.source_metadata["imap_uid"] == 1002

    await adapter.acknowledge(pkg_first.package_id)
    await adapter.acknowledge(pkg_second.package_id)
    assert backend.seen_uids == {1001, 1002}
    assert backend.flagged == {}

    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg_first.package_id)


@pytest.mark.asyncio
async def test_email_source_reject_oversize_attachment(
    phase_1b_storage_root: Path,
) -> None:
    """Oversize attachment → no package yielded, backend flagged with size_exceeded."""
    tenant_id = f"tenant-e2e-email-oversize-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / "email_oversize"

    huge = b"A" * 50_000
    msg = _make_multipart_with_attachments(
        subject="oversize",
        sender="spam@example.com",
        body="big attachment below",
        attachments=[("huge.bin", "application/octet-stream", huge)],
    )
    backend = FakeImapBackend([(2001, msg)])

    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_package_bytes=1_024,
    )

    assert await adapter.fetch_next() is None
    assert backend.flagged.get(2001) == "size_exceeded"
    assert 2001 not in backend.seen_uids

    tenant_dir = storage_root / tenant_id
    leaked_files: list[Path] = []
    if tenant_dir.exists():
        leaked_files = [p for p in tenant_dir.rglob("*") if p.is_file()]
    assert leaked_files == [], f"oversize attachment leaked to storage: {leaked_files}"

    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(uuid4())
