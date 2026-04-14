"""Intake-specific exceptions."""

from __future__ import annotations

from aiflow.core.errors import AIFlowError

__all__ = [
    "InvalidIntakePackageError",
    "InvalidStateTransitionError",
    "FileAssociationError",
]


class InvalidIntakePackageError(AIFlowError):
    error_code = "INVALID_INTAKE_PACKAGE"
    is_transient = False


class InvalidStateTransitionError(AIFlowError):
    error_code = "INVALID_STATE_TRANSITION"
    is_transient = False


class FileAssociationError(AIFlowError):
    error_code = "FILE_ASSOCIATION_ERROR"
    is_transient = False
