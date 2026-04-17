"""IntakePackageSink — Phase 1d / G0.2 adapter→repository orchestrator.

Source: architect verdict on 01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md
Day 1 — Option B (external orchestrator) wins over Option A (base-class
method). The sink keeps :class:`SourceAdapter` subclasses pure I/O
transformers; all 5 adapters (Email, File, Folder, Batch, Api) are threaded
through this sink by their caller (worker loop, test harness, or the
HTTP ``upload-package`` route in a future refactor).

Lifecycle per package::

    pkg = await adapter.fetch_next()
    if pkg is not None:
        await sink.handle(pkg)                  # associator + insert + emit
        await adapter.acknowledge(pkg.package_id)

Or, via the helper that encodes the canonical sequence::

    await process_next(adapter, sink)           # one line, correct order
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from aiflow.intake.association import resolve_mode_and_associations
from aiflow.sources.observability import emit_package_event

if TYPE_CHECKING:
    from aiflow.intake.package import IntakePackage
    from aiflow.sources.base import SourceAdapter
    from aiflow.state.repositories.intake import IntakeRepository

__all__ = [
    "IntakePackageSink",
    "process_next",
]

logger = structlog.get_logger(__name__)


# Map IntakeSourceType enum values to the short canonical source-type label
# used by the observability event payload (`file`, `folder`, `batch`, `api`,
# `email`). Mirrors the labels hardcoded by each adapter in their own legacy
# event emit sites.
_SOURCE_TYPE_LABELS: dict[str, str] = {
    "FILE_UPLOAD": "file",
    "FOLDER_IMPORT": "folder",
    "BATCH_IMPORT": "batch",
    "API_PUSH": "api",
    "EMAIL": "email",
}


class IntakePackageSink:
    """Orchestrator that persists :class:`IntakePackage` produced by adapters.

    Single persistence path for every source. Runs the shared associator
    helper (no-op when ``package.association_mode`` is already set — see
    :class:`BatchSourceAdapter` which pre-associates) and calls
    :meth:`IntakeRepository.insert_package`, then emits the canonical
    ``source.package_persisted`` event.
    """

    def __init__(self, *, repo: IntakeRepository) -> None:
        self._repo = repo

    async def handle(self, package: IntakePackage) -> None:
        """Associate (if needed), persist, and emit the persisted event."""
        if package.association_mode is None:
            resolve_mode_and_associations(package)

        await self._repo.insert_package(package)

        label = _SOURCE_TYPE_LABELS.get(package.source_type.value, package.source_type.value)
        emit_package_event(
            "source.package_persisted",
            package,
            source_type=label,
            file_count=len(package.files),
            description_count=len(package.descriptions),
            association_mode=(package.association_mode.value if package.association_mode else None),
        )


async def process_next(adapter: SourceAdapter, sink: IntakePackageSink) -> bool:
    """Drain one package from ``adapter`` through ``sink``, then acknowledge.

    Returns True if a package was processed, False when the adapter is idle.
    The canonical sequence is **fetch → handle → acknowledge** — callers
    should prefer this helper over composing the three steps manually so
    that the ack-before-persist or forgotten-ack classes of bug are
    impossible by construction.
    """
    package = await adapter.fetch_next()
    if package is None:
        return False
    await sink.handle(package)
    await adapter.acknowledge(package.package_id)
    return True
