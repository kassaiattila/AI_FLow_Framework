"""AIFlow Intake module — multi-source intake domain contracts + state machines.

Phase 1a foundation (v2.0.0).
Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md, 100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md
"""

from aiflow.intake.exceptions import (
    FileAssociationError,
    InvalidIntakePackageError,
    InvalidStateTransitionError,
)
from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakePackageStatus,
    IntakeSourceType,
)
from aiflow.intake.state_machine import (
    FILE_SM,
    PACKAGE_SM,
    IntakeFileStatus,
    IntakeStateMachine,
    TransitionRecord,
    is_terminal_status,
    validate_file_transition,
    validate_package_transition,
)

__all__ = [
    "DescriptionRole",
    "FILE_SM",
    "FileAssociationError",
    "IntakeDescription",
    "IntakeFile",
    "IntakeFileStatus",
    "IntakePackage",
    "IntakePackageStatus",
    "IntakeSourceType",
    "IntakeStateMachine",
    "InvalidIntakePackageError",
    "InvalidStateTransitionError",
    "PACKAGE_SM",
    "TransitionRecord",
    "is_terminal_status",
    "validate_file_transition",
    "validate_package_transition",
]
