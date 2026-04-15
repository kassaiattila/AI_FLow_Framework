"""E2E — FileSourceAdapter (Week 1 Day 5 / E1.4).

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, intake, source_adapter, file_upload]

Real pipeline: FileSourceAdapter.enqueue → IntakePackage → real-disk spill →
PolicyEngine tenant merge → acknowledge() idempotency. No mocks per CLAUDE.md.

DB persistence round-trip is intentionally NOT exercised here: per
feedback_asyncpg_pool_event_loop.md the module-level asyncpg pool is bound
to the first event loop, so multiple function-scoped async tests all reaching
for the pool crash with InterfaceError. The real-DB contract lives in
test_alembic_034.py (single merged method); this test stays storage-only.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import DescriptionRole, IntakePackage, IntakeSourceType
from aiflow.policy.engine import PolicyEngine
from aiflow.sources import FileSourceAdapter, SourceAdapterError
from aiflow.sources.registry import SourceAdapterRegistry


@pytest.mark.asyncio
async def test_file_source_happy_path(
    phase_1b_storage_root: Path,
    phase_1b_source_registry: SourceAdapterRegistry,
    phase_1b_policy_engine: PolicyEngine,
) -> None:
    """enqueue → fetch_next → PolicyEngine resolve → acknowledge (idempotent)."""
    tenant_id = f"tenant-e2e-file-happy-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / "file_happy"
    payload = b"%PDF-1.4 sample invoice bytes for E2E\n"
    expected_sha = hashlib.sha256(payload).hexdigest()

    adapter = FileSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_package_bytes=10_000,
    )
    phase_1b_source_registry.register(FileSourceAdapter)
    assert phase_1b_source_registry.has(IntakeSourceType.FILE_UPLOAD)

    returned = adapter.enqueue(
        raw_bytes=payload,
        filename="invoice.pdf",
        description="weekly batch upload",
    )
    assert isinstance(returned, IntakePackage)
    assert returned.source_type == IntakeSourceType.FILE_UPLOAD

    drained = await adapter.fetch_next()
    assert drained is not None
    assert drained.package_id == returned.package_id
    assert drained.tenant_id == tenant_id
    assert len(drained.files) == 1
    assert len(drained.descriptions) == 1
    assert drained.descriptions[0].role == DescriptionRole.USER_NOTE

    intake_file = drained.files[0]
    assert intake_file.sha256 == expected_sha
    assert intake_file.size_bytes == len(payload)
    on_disk = Path(intake_file.file_path)
    assert on_disk.exists()
    assert on_disk.read_bytes() == payload
    assert on_disk.is_relative_to(storage_root / tenant_id / str(drained.package_id))

    tenant_policy = phase_1b_policy_engine.get_for_tenant(tenant_id)
    assert tenant_policy is not None

    await adapter.acknowledge(drained.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(drained.package_id)

    assert await adapter.fetch_next() is None


@pytest.mark.asyncio
async def test_file_source_size_guard_rejects_before_storage(
    phase_1b_storage_root: Path,
) -> None:
    """Oversize upload raises SourceAdapterError; nothing reaches the queue or disk."""
    tenant_id = f"tenant-e2e-file-oversize-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / "file_oversize"
    adapter = FileSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_package_bytes=16,
    )

    oversized = b"X" * 4096

    with pytest.raises(SourceAdapterError, match="exceeds max_package_bytes"):
        adapter.enqueue(raw_bytes=oversized, filename="huge.bin")

    assert await adapter.fetch_next() is None

    tenant_dir = storage_root / tenant_id
    if tenant_dir.exists():
        leaked = [p for p in tenant_dir.rglob("*") if p.is_file()]
        assert leaked == [], f"size-rejected bytes leaked onto disk: {leaked}"
