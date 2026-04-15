"""Unit tests for SourceAdapterRegistry (Phase 1b — Week 1 Day 1 — E0.2)."""

from __future__ import annotations

from uuid import UUID

import pytest

from aiflow.intake.package import (
    IntakeDescription,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources import (
    DuplicateAdapterError,
    InvalidAdapterError,
    SourceAdapter,
    SourceAdapterMetadata,
    SourceAdapterRegistry,
    UnknownSourceTypeError,
)


def _make_adapter(
    cls_name: str,
    src: IntakeSourceType,
    *,
    meta_name: str | None = None,
) -> type[SourceAdapter]:
    """Build a concrete SourceAdapter subclass bound to `src`."""

    adapter_src = src
    adapter_meta_name = meta_name or f"{cls_name.lower()}_stub"

    class _Adapter(SourceAdapter):
        source_type = adapter_src

        @property
        def metadata(self) -> SourceAdapterMetadata:
            return SourceAdapterMetadata(
                name=adapter_meta_name,
                version="0.1.0",
                source_type=adapter_src,
                transport="pull",
            )

        async def fetch_next(self) -> IntakePackage | None:
            return IntakePackage(
                source_type=adapter_src,
                tenant_id="t",
                descriptions=[IntakeDescription(text="x")],
            )

        async def acknowledge(self, package_id: UUID) -> None:  # noqa: ARG002
            return None

        async def reject(self, package_id: UUID, reason: str) -> None:  # noqa: ARG002
            return None

        async def health_check(self) -> bool:
            return True

    _Adapter.__name__ = cls_name
    return _Adapter


# --- register / get --------------------------------------------------------


def test_register_and_get_returns_class() -> None:
    registry = SourceAdapterRegistry()
    email_adapter = _make_adapter("EmailAdapter", IntakeSourceType.EMAIL)
    registry.register(email_adapter)
    assert registry.get(IntakeSourceType.EMAIL) is email_adapter


def test_get_unknown_source_type_raises() -> None:
    registry = SourceAdapterRegistry()
    with pytest.raises(UnknownSourceTypeError):
        registry.get(IntakeSourceType.EMAIL)


def test_register_duplicate_source_type_raises() -> None:
    registry = SourceAdapterRegistry()
    adapter_a = _make_adapter("AdapterA", IntakeSourceType.EMAIL, meta_name="a")
    adapter_b = _make_adapter("AdapterB", IntakeSourceType.EMAIL, meta_name="b")
    registry.register(adapter_a)
    with pytest.raises(DuplicateAdapterError):
        registry.register(adapter_b)


def test_register_same_class_twice_is_idempotent() -> None:
    registry = SourceAdapterRegistry()
    adapter_a = _make_adapter("AdapterA", IntakeSourceType.EMAIL)
    registry.register(adapter_a)
    registry.register(adapter_a)  # no-op, same class
    assert registry.get(IntakeSourceType.EMAIL) is adapter_a


def test_register_non_adapter_class_raises() -> None:
    registry = SourceAdapterRegistry()

    class NotAnAdapter:
        source_type = IntakeSourceType.EMAIL

    with pytest.raises(InvalidAdapterError):
        registry.register(NotAnAdapter)  # type: ignore[arg-type]


def test_register_adapter_without_source_type_raises() -> None:
    registry = SourceAdapterRegistry()

    class _Bad(SourceAdapter):
        # source_type intentionally missing / not IntakeSourceType
        source_type = "email"  # type: ignore[assignment]

        @property
        def metadata(self) -> SourceAdapterMetadata:
            raise NotImplementedError

        async def fetch_next(self) -> IntakePackage | None:
            return None

        async def acknowledge(self, package_id: UUID) -> None:  # noqa: ARG002
            return None

        async def reject(self, package_id: UUID, reason: str) -> None:  # noqa: ARG002
            return None

        async def health_check(self) -> bool:
            return True

    with pytest.raises(InvalidAdapterError):
        registry.register(_Bad)


# --- listing / membership --------------------------------------------------


def test_list_source_types_is_sorted_and_deterministic() -> None:
    registry = SourceAdapterRegistry()
    registry.register(_make_adapter("EmailAdapter", IntakeSourceType.EMAIL))
    registry.register(_make_adapter("FileAdapter", IntakeSourceType.FILE_UPLOAD))
    registry.register(_make_adapter("ApiAdapter", IntakeSourceType.API_PUSH))
    types = registry.list_source_types()
    assert types == sorted(types, key=lambda st: st.value)
    assert set(types) == {
        IntakeSourceType.EMAIL,
        IntakeSourceType.FILE_UPLOAD,
        IntakeSourceType.API_PUSH,
    }


def test_list_all_returns_metadata_for_no_arg_adapters() -> None:
    registry = SourceAdapterRegistry()
    registry.register(_make_adapter("EmailAdapter", IntakeSourceType.EMAIL, meta_name="email_x"))
    registry.register(
        _make_adapter("FileAdapter", IntakeSourceType.FILE_UPLOAD, meta_name="file_x")
    )
    metadatas = registry.list_all()
    names = {m.name for m in metadatas}
    assert names == {"email_x", "file_x"}


def test_list_all_skips_adapters_requiring_ctor_args() -> None:
    registry = SourceAdapterRegistry()

    class _NeedsCfg(SourceAdapter):
        source_type = IntakeSourceType.BATCH_IMPORT

        def __init__(self, cfg: dict) -> None:
            self._cfg = cfg

        @property
        def metadata(self) -> SourceAdapterMetadata:
            return SourceAdapterMetadata(
                name="batch_needs_cfg",
                version="0.1.0",
                source_type=IntakeSourceType.BATCH_IMPORT,
                transport="pull",
            )

        async def fetch_next(self) -> IntakePackage | None:
            return None

        async def acknowledge(self, package_id: UUID) -> None:  # noqa: ARG002
            return None

        async def reject(self, package_id: UUID, reason: str) -> None:  # noqa: ARG002
            return None

        async def health_check(self) -> bool:
            return True

    registry.register(_NeedsCfg)
    assert registry.list_all() == []  # ctor-arg adapter silently skipped


def test_has_and_contains() -> None:
    registry = SourceAdapterRegistry()
    registry.register(_make_adapter("EmailAdapter", IntakeSourceType.EMAIL))
    assert registry.has(IntakeSourceType.EMAIL)
    assert IntakeSourceType.EMAIL in registry
    assert not registry.has(IntakeSourceType.API_PUSH)
    assert IntakeSourceType.API_PUSH not in registry


def test_len_reflects_registered_count() -> None:
    registry = SourceAdapterRegistry()
    assert len(registry) == 0
    registry.register(_make_adapter("EmailAdapter", IntakeSourceType.EMAIL))
    registry.register(_make_adapter("FileAdapter", IntakeSourceType.FILE_UPLOAD))
    assert len(registry) == 2


def test_unregister_removes_adapter() -> None:
    registry = SourceAdapterRegistry()
    registry.register(_make_adapter("EmailAdapter", IntakeSourceType.EMAIL))
    assert registry.has(IntakeSourceType.EMAIL)
    registry.unregister(IntakeSourceType.EMAIL)
    assert not registry.has(IntakeSourceType.EMAIL)
    # unregister is idempotent
    registry.unregister(IntakeSourceType.EMAIL)


def test_fresh_registry_instances_are_independent() -> None:
    r1 = SourceAdapterRegistry()
    r2 = SourceAdapterRegistry()
    r1.register(_make_adapter("EmailAdapter", IntakeSourceType.EMAIL))
    assert r1.has(IntakeSourceType.EMAIL)
    assert not r2.has(IntakeSourceType.EMAIL)


# --- real EmailSourceAdapter registration (E1.1-A) -------------------------


def test_register_real_email_source_adapter() -> None:
    """The production EmailSourceAdapter must register under IntakeSourceType.EMAIL."""
    from aiflow.sources import EmailSourceAdapter

    registry = SourceAdapterRegistry()
    registry.register(EmailSourceAdapter)
    assert registry.get(IntakeSourceType.EMAIL) is EmailSourceAdapter
    assert registry.has(IntakeSourceType.EMAIL)
    # EmailSourceAdapter requires ctor args → list_all skips it silently.
    assert registry.list_all() == []


# --- real FileSourceAdapter registration (E1.3) ---------------------------


def test_register_real_file_source_adapter() -> None:
    """The production FileSourceAdapter must register under IntakeSourceType.FILE_UPLOAD."""
    from aiflow.sources import FileSourceAdapter

    registry = SourceAdapterRegistry()
    registry.register(FileSourceAdapter)
    assert registry.get(IntakeSourceType.FILE_UPLOAD) is FileSourceAdapter
    assert registry.has(IntakeSourceType.FILE_UPLOAD)
    # FileSourceAdapter requires ctor args → list_all skips it silently.
    assert registry.list_all() == []


def test_file_adapter_duplicate_registration_raises() -> None:
    from aiflow.sources import FileSourceAdapter

    registry = SourceAdapterRegistry()
    registry.register(FileSourceAdapter)

    other = _make_adapter("AlternativeFileAdapter", IntakeSourceType.FILE_UPLOAD)
    with pytest.raises(DuplicateAdapterError):
        registry.register(other)


def test_email_and_file_adapters_coexist_in_registry() -> None:
    """Both production adapters must co-exist under their respective source types."""
    from aiflow.sources import EmailSourceAdapter, FileSourceAdapter

    registry = SourceAdapterRegistry()
    registry.register(EmailSourceAdapter)
    registry.register(FileSourceAdapter)
    assert registry.get(IntakeSourceType.EMAIL) is EmailSourceAdapter
    assert registry.get(IntakeSourceType.FILE_UPLOAD) is FileSourceAdapter
    assert set(registry.list_source_types()) == {
        IntakeSourceType.EMAIL,
        IntakeSourceType.FILE_UPLOAD,
    }
