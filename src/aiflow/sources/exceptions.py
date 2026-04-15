"""Exceptions for the source adapter registry.

Source: 01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 1 Day 1 — E0.2).
"""

from __future__ import annotations

from aiflow.core.errors import AIFlowError

__all__ = [
    "SourceAdapterError",
    "DuplicateAdapterError",
    "UnknownSourceTypeError",
    "InvalidAdapterError",
]


class SourceAdapterError(AIFlowError):
    """Base class for source-adapter registry errors."""


class DuplicateAdapterError(SourceAdapterError):
    """Raised when two adapters claim the same IntakeSourceType."""


class UnknownSourceTypeError(SourceAdapterError):
    """Raised when no adapter is registered for a requested IntakeSourceType."""


class InvalidAdapterError(SourceAdapterError):
    """Raised when a registered class is not a SourceAdapter subclass or is missing source_type."""
