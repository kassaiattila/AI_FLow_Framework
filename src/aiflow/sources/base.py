"""Abstract source adapter interface — produces IntakePackage from external inputs.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N2 + R1,
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 0 Day 0).
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from aiflow.intake.package import IntakeSourceType

if TYPE_CHECKING:
    from aiflow.intake.package import IntakePackage

__all__ = [
    "SourceAdapter",
    "SourceAdapterMetadata",
]


class SourceAdapterMetadata(BaseModel):
    """Descriptor for a source adapter's capabilities and constraints."""

    name: str = Field(
        ...,
        min_length=1,
        description="Adapter identifier (e.g. 'email_imap', 'file_upload').",
    )
    version: str = Field(..., min_length=1, description="Semver version string.")
    source_type: IntakeSourceType = Field(
        ..., description="IntakePackage source_type this adapter produces."
    )
    supports_batching: bool = Field(
        default=False,
        description="Whether a single poll can yield multiple packages.",
    )
    requires_ack: bool = Field(
        default=True,
        description="Whether the upstream source expects acknowledgement (e.g. IMAP flag, webhook 200).",
    )
    transport: Literal["push", "pull"] = Field(
        ...,
        description="'pull' = we fetch (IMAP, folder watch, batch). 'push' = upstream calls us (webhook, upload).",
    )
    max_package_bytes: int | None = Field(
        default=None,
        ge=1,
        description="Optional per-package size guard (None = adapter-defined default).",
    )


class SourceAdapter(abc.ABC):
    """Abstract interface for source adapters.

    Lifecycle per package:
      1. fetch_next()   → returns IntakePackage or None when idle
      2. acknowledge()  → mark upstream success (required if metadata.requires_ack)
      3. reject()       → mark upstream failure with reason (required if metadata.requires_ack)

    Concrete subclasses MUST set `source_type` ClassVar matching their metadata.
    """

    source_type: ClassVar[IntakeSourceType]

    @property
    @abc.abstractmethod
    def metadata(self) -> SourceAdapterMetadata:
        """Adapter capability descriptor."""

    @abc.abstractmethod
    async def fetch_next(self) -> IntakePackage | None:
        """Fetch the next available package or None if the source is idle."""

    @abc.abstractmethod
    async def acknowledge(self, package_id: UUID) -> None:
        """Acknowledge successful handoff of a package to upstream."""

    @abc.abstractmethod
    async def reject(self, package_id: UUID, reason: str) -> None:
        """Reject a package upstream with a reason (e.g. policy violation, size guard)."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the adapter can reach its upstream source."""
