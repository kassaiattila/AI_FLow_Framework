"""State machines for IntakePackage and IntakeFile lifecycle.

Source: 100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md Sections 1-2 (SIGNED OFF v2.0)

Idempotent replay: applying a transition to the current state is a no-op.
Terminal states: no outgoing transitions allowed.
Every transition records timestamp + actor_id for audit.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aiflow.intake.exceptions import InvalidStateTransitionError
from aiflow.intake.package import IntakePackageStatus

__all__ = [
    "IntakeFileStatus",
    "TransitionRecord",
    "IntakeStateMachine",
    "PACKAGE_SM",
    "FILE_SM",
    "validate_package_transition",
    "validate_file_transition",
    "is_terminal_status",
]


class IntakeFileStatus(str, Enum):
    """Per-file lifecycle status (see 100_c Section 2.1)."""

    PENDING = "pending"
    ROUTED = "routed"
    PARSED = "parsed"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    ARCHIVED = "archived"
    FAILED = "failed"


class TransitionRecord(BaseModel):
    """Audit record for a state transition."""

    from_status: str
    to_status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor_id: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Transition maps (source: 100_c Section 1.3 + 2.2) ---

_PACKAGE_TRANSITIONS: dict[Enum, set[Enum]] = {
    IntakePackageStatus.RECEIVED: {IntakePackageStatus.NORMALIZED, IntakePackageStatus.FAILED},
    IntakePackageStatus.NORMALIZED: {IntakePackageStatus.ROUTED, IntakePackageStatus.FAILED},
    IntakePackageStatus.ROUTED: {IntakePackageStatus.PARSED, IntakePackageStatus.FAILED},
    IntakePackageStatus.PARSED: {IntakePackageStatus.CLASSIFIED, IntakePackageStatus.FAILED},
    IntakePackageStatus.CLASSIFIED: {
        IntakePackageStatus.EXTRACTED,
        IntakePackageStatus.REVIEW_PENDING,
        IntakePackageStatus.FAILED,
    },
    IntakePackageStatus.EXTRACTED: {
        IntakePackageStatus.REVIEW_PENDING,
        IntakePackageStatus.ARCHIVED,
        IntakePackageStatus.FAILED,
    },
    IntakePackageStatus.REVIEW_PENDING: {IntakePackageStatus.REVIEWED, IntakePackageStatus.FAILED},
    IntakePackageStatus.REVIEWED: {
        IntakePackageStatus.EXTRACTED,
        IntakePackageStatus.ARCHIVED,
        IntakePackageStatus.FAILED,
    },
    IntakePackageStatus.ARCHIVED: set(),
    IntakePackageStatus.FAILED: {IntakePackageStatus.RECEIVED, IntakePackageStatus.NORMALIZED},
    IntakePackageStatus.QUARANTINED: set(),
}

_PACKAGE_TERMINAL: set[Enum] = {
    IntakePackageStatus.ARCHIVED,
    IntakePackageStatus.QUARANTINED,
}

_FILE_TRANSITIONS: dict[Enum, set[Enum]] = {
    IntakeFileStatus.PENDING: {IntakeFileStatus.ROUTED, IntakeFileStatus.FAILED},
    IntakeFileStatus.ROUTED: {IntakeFileStatus.PARSED, IntakeFileStatus.FAILED},
    IntakeFileStatus.PARSED: {IntakeFileStatus.CLASSIFIED, IntakeFileStatus.FAILED},
    IntakeFileStatus.CLASSIFIED: {IntakeFileStatus.EXTRACTED, IntakeFileStatus.FAILED},
    IntakeFileStatus.EXTRACTED: {IntakeFileStatus.ARCHIVED, IntakeFileStatus.FAILED},
    IntakeFileStatus.ARCHIVED: set(),
    IntakeFileStatus.FAILED: {IntakeFileStatus.PENDING},
}

_FILE_TERMINAL: set[Enum] = {
    IntakeFileStatus.ARCHIVED,
}


class IntakeStateMachine:
    """Generic state machine with idempotent transitions and recovery.

    Usage::

        sm = IntakeStateMachine(transitions=_PACKAGE_TRANSITIONS, terminal=_PACKAGE_TERMINAL)
        sm.validate(IntakePackageStatus.RECEIVED, IntakePackageStatus.NORMALIZED)
        record = sm.apply(package, IntakePackageStatus.NORMALIZED, actor_id="normalizer")
    """

    def __init__(
        self,
        transitions: dict[Enum, set[Enum]],
        terminal: set[Enum],
    ) -> None:
        self._transitions = transitions
        self._terminal = terminal

    def validate(self, from_status: Enum, to_status: Enum) -> None:
        """Raise InvalidStateTransitionError if transition is not allowed."""
        allowed = self._transitions.get(from_status, set())
        if to_status not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid transition: {from_status.value} → {to_status.value}. "
                f"Allowed: {sorted(s.value for s in allowed) if allowed else 'terminal (no transitions)'}",
            )

    def apply(
        self,
        entity: Any,
        to_status: Enum,
        *,
        actor_id: str = "system",
        metadata: dict[str, Any] | None = None,
        status_field: str = "status",
    ) -> TransitionRecord | None:
        """Apply a transition. Returns TransitionRecord, or None if idempotent no-op.

        Idempotent: if entity is already in to_status, returns None (no-op).
        """
        current = getattr(entity, status_field)
        if current == to_status:
            return None

        self.validate(current, to_status)

        record = TransitionRecord(
            from_status=current.value,
            to_status=to_status.value,
            actor_id=actor_id,
            metadata=metadata or {},
        )

        if hasattr(entity, status_field):
            setattr(entity, status_field, to_status)

        return record

    def is_terminal(self, status: Enum) -> bool:
        return status in self._terminal

    def get_allowed(self, status: Enum) -> set[Enum]:
        return self._transitions.get(status, set())

    def get_resumable_targets(self) -> set[Enum]:
        """Return states that FAILED can resume to."""
        failed_targets = set()
        for status in self._transitions:
            if status.value == "failed":
                failed_targets = self._transitions[status]
                break
        return failed_targets

    def resume_from_checkpoint(
        self,
        entity: Any,
        target_status: Enum,
        *,
        actor_id: str = "admin",
        status_field: str = "status",
    ) -> TransitionRecord | None:
        """Resume a FAILED entity to a specific checkpoint state."""
        current = getattr(entity, status_field)
        if current.value != "failed":
            raise InvalidStateTransitionError(
                f"resume_from_checkpoint only works from FAILED state, got: {current.value}",
            )
        return self.apply(entity, target_status, actor_id=actor_id, status_field=status_field)


PACKAGE_SM = IntakeStateMachine(transitions=_PACKAGE_TRANSITIONS, terminal=_PACKAGE_TERMINAL)
FILE_SM = IntakeStateMachine(transitions=_FILE_TRANSITIONS, terminal=_FILE_TERMINAL)


def validate_package_transition(
    from_status: IntakePackageStatus,
    to_status: IntakePackageStatus,
) -> None:
    """Raise InvalidStateTransitionError if package transition is not valid."""
    PACKAGE_SM.validate(from_status, to_status)


def validate_file_transition(
    from_status: IntakeFileStatus,
    to_status: IntakeFileStatus,
) -> None:
    """Raise InvalidStateTransitionError if file transition is not valid."""
    FILE_SM.validate(from_status, to_status)


def is_terminal_status(status: IntakePackageStatus | IntakeFileStatus) -> bool:
    """Check if a status is terminal (no further transitions allowed)."""
    if isinstance(status, IntakePackageStatus):
        return PACKAGE_SM.is_terminal(status)
    return FILE_SM.is_terminal(status)
