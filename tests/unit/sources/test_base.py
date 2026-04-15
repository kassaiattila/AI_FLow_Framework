"""Contract tests for the SourceAdapter ABC (Phase 1b — Week 0 Day 0)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from aiflow.intake.package import (
    IntakeDescription,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources import SourceAdapter, SourceAdapterMetadata


class _StubSourceAdapter(SourceAdapter):
    """Concrete stub used to exercise the SourceAdapter contract."""

    source_type = IntakeSourceType.FILE_UPLOAD

    def __init__(self) -> None:
        self.ack_calls: list[UUID] = []
        self.reject_calls: list[tuple[UUID, str]] = []
        self._metadata = SourceAdapterMetadata(
            name="stub_file",
            version="0.1.0",
            source_type=IntakeSourceType.FILE_UPLOAD,
            supports_batching=False,
            requires_ack=True,
            transport="push",
            max_package_bytes=1024,
        )

    @property
    def metadata(self) -> SourceAdapterMetadata:
        return self._metadata

    async def fetch_next(self) -> IntakePackage | None:
        return IntakePackage(
            source_type=IntakeSourceType.FILE_UPLOAD,
            tenant_id="tenant-a",
            descriptions=[IntakeDescription(text="stub description")],
        )

    async def acknowledge(self, package_id: UUID) -> None:
        self.ack_calls.append(package_id)

    async def reject(self, package_id: UUID, reason: str) -> None:
        self.reject_calls.append((package_id, reason))

    async def health_check(self) -> bool:
        return True


def test_source_adapter_abc_cannot_instantiate() -> None:
    with pytest.raises(TypeError):
        SourceAdapter()  # type: ignore[abstract]


def test_source_adapter_metadata_roundtrip() -> None:
    meta = SourceAdapterMetadata(
        name="email_imap",
        version="1.0.0",
        source_type=IntakeSourceType.EMAIL,
        supports_batching=True,
        requires_ack=True,
        transport="pull",
    )
    assert meta.name == "email_imap"
    assert meta.source_type is IntakeSourceType.EMAIL
    assert meta.supports_batching is True
    assert meta.max_package_bytes is None


def test_source_adapter_metadata_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        SourceAdapterMetadata(
            name="",
            version="1.0.0",
            source_type=IntakeSourceType.EMAIL,
            transport="pull",
        )


def test_source_adapter_metadata_rejects_invalid_transport() -> None:
    with pytest.raises(ValidationError):
        SourceAdapterMetadata(
            name="x",
            version="1.0.0",
            source_type=IntakeSourceType.EMAIL,
            transport="sideways",  # type: ignore[arg-type]
        )


def test_source_adapter_metadata_rejects_zero_max_bytes() -> None:
    with pytest.raises(ValidationError):
        SourceAdapterMetadata(
            name="x",
            version="1.0.0",
            source_type=IntakeSourceType.EMAIL,
            transport="pull",
            max_package_bytes=0,
        )


def test_stub_source_adapter_can_instantiate() -> None:
    adapter = _StubSourceAdapter()
    assert adapter.metadata.name == "stub_file"
    assert adapter.source_type is IntakeSourceType.FILE_UPLOAD


@pytest.mark.asyncio
async def test_fetch_next_returns_intake_package() -> None:
    adapter = _StubSourceAdapter()
    pkg = await adapter.fetch_next()
    assert pkg is not None
    assert pkg.source_type is IntakeSourceType.FILE_UPLOAD
    assert pkg.tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_acknowledge_records_package_id() -> None:
    adapter = _StubSourceAdapter()
    pkg_id = uuid4()
    await adapter.acknowledge(pkg_id)
    assert adapter.ack_calls == [pkg_id]


@pytest.mark.asyncio
async def test_reject_records_reason() -> None:
    adapter = _StubSourceAdapter()
    pkg_id = uuid4()
    await adapter.reject(pkg_id, reason="policy_violation")
    assert adapter.reject_calls == [(pkg_id, "policy_violation")]


@pytest.mark.asyncio
async def test_health_check_returns_bool() -> None:
    adapter = _StubSourceAdapter()
    assert await adapter.health_check() is True


def test_metadata_source_type_matches_classvar() -> None:
    adapter = _StubSourceAdapter()
    assert adapter.metadata.source_type is adapter.source_type


def test_missing_abstract_method_keeps_class_abstract() -> None:
    class _PartialAdapter(SourceAdapter):
        source_type = IntakeSourceType.EMAIL

        @property
        def metadata(self) -> SourceAdapterMetadata:  # type: ignore[override]
            raise NotImplementedError

    with pytest.raises(TypeError):
        _PartialAdapter()  # type: ignore[abstract]
