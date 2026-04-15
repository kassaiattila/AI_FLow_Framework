"""Source adapters — raw input → IntakePackage.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N2 (email) + R1 (file) + N4 (association),
        01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Phase 1b sprint plan).
"""

from __future__ import annotations

from aiflow.sources.base import SourceAdapter, SourceAdapterMetadata

__all__ = [
    "SourceAdapter",
    "SourceAdapterMetadata",
]
