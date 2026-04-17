"""IntakePackageSink unit tests — Phase 1d G0.2.

@test_registry:
    suite: core-unit
    component: sources.sink
    covers: [src/aiflow/sources/sink.py]
    phase: 1d
    priority: high
    estimated_duration_ms: 500
    requires_services: []
    tags: [sources, sink, phase_1d]

The sink orchestrates adapter output → associator → `IntakeRepository.insert_package`
→ canonical `source.package_persisted` event. These tests cover the pure
logic: associator is run when needed, skipped when the package is already
associated (e.g. BatchSourceAdapter), and the canonical event carries the
full contract shape. Real-Postgres E2E coverage lives in
`tests/e2e/sources/test_email_adapter_persistence.py`.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from aiflow.intake.package import (
    AssociationMode,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources.sink import IntakePackageSink, process_next


class _FakeRepo:
    def __init__(self) -> None:
        self.inserted: list[IntakePackage] = []

    async def insert_package(self, package: IntakePackage) -> None:
        self.inserted.append(package)


def _make_file(name: str = "doc.pdf") -> IntakeFile:
    return IntakeFile(
        file_path=f"/tmp/{name}",
        file_name=name,
        mime_type="application/pdf",
        size_bytes=10,
        sha256="0" * 64,
        sequence_index=0,
    )


def _make_pkg(
    *,
    files: list[IntakeFile] | None = None,
    descriptions: list[IntakeDescription] | None = None,
    association_mode: AssociationMode | None = None,
    source_type: IntakeSourceType = IntakeSourceType.EMAIL,
) -> IntakePackage:
    return IntakePackage(
        package_id=uuid4(),
        source_type=source_type,
        tenant_id="tenant-sink",
        files=files if files is not None else [_make_file()],
        descriptions=descriptions or [],
        association_mode=association_mode,
    )


@pytest.mark.asyncio
async def test_handle_persists_and_emits_canonical_persisted() -> None:
    repo = _FakeRepo()
    sink = IntakePackageSink(repo=repo)  # type: ignore[arg-type]
    pkg = _make_pkg()

    with capture_logs() as events:
        await sink.handle(pkg)

    assert repo.inserted == [pkg]
    persisted = [e for e in events if e.get("event") == "source.package_persisted"]
    assert len(persisted) == 1
    rec = persisted[0]
    assert rec["source_type"] == "email"
    assert rec["tenant_id"] == "tenant-sink"
    assert rec["file_count"] == 1
    assert rec["description_count"] == 0
    assert rec["association_mode"] is None


@pytest.mark.asyncio
async def test_handle_runs_associator_when_mode_missing() -> None:
    repo = _FakeRepo()
    sink = IntakePackageSink(repo=repo)  # type: ignore[arg-type]
    # N files == N descriptions, no mode set → ORDER is inferred.
    f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
    d1, d2 = IntakeDescription(text="d1"), IntakeDescription(text="d2")
    pkg = _make_pkg(files=[f1, f2], descriptions=[d1, d2])

    await sink.handle(pkg)

    assert pkg.association_mode is AssociationMode.ORDER
    d1_after = next(d for d in pkg.descriptions if d.description_id == d1.description_id)
    assert d1_after.associated_file_ids == [f1.file_id]


@pytest.mark.asyncio
async def test_handle_skips_associator_when_mode_already_set() -> None:
    """BatchSourceAdapter already runs the associator; sink must not re-run it."""
    repo = _FakeRepo()
    sink = IntakePackageSink(repo=repo)  # type: ignore[arg-type]
    f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
    d1 = IntakeDescription(text="sole")
    # Pre-wired: SINGLE_DESCRIPTION mode, associated_file_ids already populated.
    d1.associated_file_ids = [f1.file_id, f2.file_id]
    pkg = _make_pkg(
        files=[f1, f2],
        descriptions=[d1],
        association_mode=AssociationMode.SINGLE_DESCRIPTION,
        source_type=IntakeSourceType.BATCH_IMPORT,
    )

    await sink.handle(pkg)

    # Mode preserved; associated_file_ids untouched.
    assert pkg.association_mode is AssociationMode.SINGLE_DESCRIPTION
    assert pkg.descriptions[0].associated_file_ids == [f1.file_id, f2.file_id]


class _FakeAdapter:
    """Minimal SourceAdapter-shaped stub for process_next() unit tests."""

    def __init__(self, packages: list[IntakePackage]) -> None:
        self._packages = list(packages)
        self.acked: list[str] = []

    async def fetch_next(self) -> IntakePackage | None:
        return self._packages.pop(0) if self._packages else None

    async def acknowledge(self, package_id) -> None:  # noqa: ANN001
        self.acked.append(str(package_id))

    async def reject(self, package_id, reason) -> None:  # noqa: ANN001, ARG002
        raise AssertionError("reject not expected in this test")


@pytest.mark.asyncio
async def test_process_next_drains_one_package_then_returns_false() -> None:
    repo = _FakeRepo()
    sink = IntakePackageSink(repo=repo)  # type: ignore[arg-type]
    pkg = _make_pkg()
    adapter = _FakeAdapter([pkg])

    assert await process_next(adapter, sink) is True  # type: ignore[arg-type]
    assert repo.inserted == [pkg]
    assert adapter.acked == [str(pkg.package_id)]

    # Subsequent call: adapter idle.
    assert await process_next(adapter, sink) is False  # type: ignore[arg-type]
