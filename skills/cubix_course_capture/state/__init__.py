"""State management for Cubix Course Capture pipeline."""

from __future__ import annotations

from enum import StrEnum

from skills.cubix_course_capture.state.file_state import FileStateManager

__all__ = ["StateBackend", "FileStateManager", "get_state_manager"]


class StateBackend(StrEnum):
    """Available state persistence backends."""

    FILE = "file"
    DATABASE = "db"
    BOTH = "both"


def get_state_manager(
    backend: StateBackend = StateBackend.FILE, **kwargs: object
) -> FileStateManager:
    """Factory for state manager instances.

    Args:
        backend: Which persistence backend to use.
        **kwargs: Passed to the state manager constructor.

    Returns:
        A configured state manager instance.

    Raises:
        NotImplementedError: For DB and dual backends (Phase 5).
    """
    if backend == StateBackend.FILE:
        return FileStateManager(**kwargs)  # type: ignore[arg-type]
    elif backend == StateBackend.DATABASE:
        raise NotImplementedError("DB state manager - Phase 5")
    else:
        raise NotImplementedError("Dual backend - Phase 5")
