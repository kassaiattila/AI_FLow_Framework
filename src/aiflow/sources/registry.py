"""SourceAdapterRegistry — IntakeSourceType → SourceAdapter class lookup.

Analogous to `aiflow.providers.registry.ProviderRegistry`: stores *classes*
so that per-tenant / per-run configs can be injected at instantiation time.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N2 + R1 + N4,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 1 Day 1 — E0.2).
"""

from __future__ import annotations

import structlog

from aiflow.intake.package import IntakeSourceType
from aiflow.sources.base import SourceAdapter, SourceAdapterMetadata
from aiflow.sources.exceptions import (
    DuplicateAdapterError,
    InvalidAdapterError,
    UnknownSourceTypeError,
)

__all__ = [
    "SourceAdapterRegistry",
]

logger = structlog.get_logger(__name__)


class SourceAdapterRegistry:
    """Central registry mapping IntakeSourceType to SourceAdapter classes.

    Each source_type may be claimed by exactly one adapter class.
    Metadata listing is derived by instantiating each adapter's metadata
    descriptor via a no-arg constructor — adapters that require config
    should expose a classmethod `describe()` returning SourceAdapterMetadata
    without side effects (future work, out of scope for E0.2).
    """

    def __init__(self) -> None:
        self._adapters: dict[IntakeSourceType, type[SourceAdapter]] = {}
        logger.info("source_adapter_registry_initialized")

    def register(self, adapter_cls: type[SourceAdapter]) -> None:
        """Register a SourceAdapter subclass keyed by its ClassVar source_type."""
        if not isinstance(adapter_cls, type) or not issubclass(adapter_cls, SourceAdapter):
            raise InvalidAdapterError(
                f"adapter_cls must be a subclass of SourceAdapter, got {adapter_cls!r}"
            )

        source_type = getattr(adapter_cls, "source_type", None)
        if not isinstance(source_type, IntakeSourceType):
            raise InvalidAdapterError(
                f"{adapter_cls.__name__} must set `source_type: ClassVar[IntakeSourceType]`"
            )

        existing = self._adapters.get(source_type)
        if existing is not None and existing is not adapter_cls:
            raise DuplicateAdapterError(
                f"source_type {source_type.value!r} already registered by "
                f"{existing.__name__}; cannot register {adapter_cls.__name__}"
            )

        self._adapters[source_type] = adapter_cls
        logger.info(
            "source_adapter_registered",
            source_type=source_type.value,
            adapter=adapter_cls.__name__,
        )

    def get(self, source_type: IntakeSourceType) -> type[SourceAdapter]:
        """Return the adapter class bound to `source_type`."""
        try:
            return self._adapters[source_type]
        except KeyError:
            raise UnknownSourceTypeError(
                f"No source adapter registered for {source_type.value!r}. "
                f"Available: {sorted(st.value for st in self._adapters)}"
            ) from None

    def unregister(self, source_type: IntakeSourceType) -> None:
        """Remove an adapter (primarily for test isolation)."""
        self._adapters.pop(source_type, None)

    def has(self, source_type: IntakeSourceType) -> bool:
        """True if an adapter is registered for `source_type`."""
        return source_type in self._adapters

    def list_source_types(self) -> list[IntakeSourceType]:
        """All registered source types, deterministic order."""
        return sorted(self._adapters.keys(), key=lambda st: st.value)

    def list_all(self) -> list[SourceAdapterMetadata]:
        """Metadata descriptors for every registered adapter.

        Skips adapters whose constructor requires runtime config (those should
        later implement a `describe()` classmethod — tracked for Week 2).
        """
        out: list[SourceAdapterMetadata] = []
        for source_type in self.list_source_types():
            adapter_cls = self._adapters[source_type]
            describe = getattr(adapter_cls, "describe", None)
            if callable(describe):
                out.append(describe())
                continue
            try:
                instance = adapter_cls()  # type: ignore[call-arg]
            except TypeError:
                logger.warning(
                    "source_adapter_metadata_skipped",
                    source_type=source_type.value,
                    adapter=adapter_cls.__name__,
                    reason="requires_constructor_args",
                )
                continue
            out.append(instance.metadata)
        return out

    def __len__(self) -> int:
        return len(self._adapters)

    def __contains__(self, source_type: object) -> bool:
        return source_type in self._adapters
