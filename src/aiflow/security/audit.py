"""Audit trail for tracking all security-relevant actions."""
from __future__ import annotations

import enum
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "AuditAction",
    "AuditEntry",
    "AuditLogger",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums & models
# ---------------------------------------------------------------------------

class AuditAction(str, enum.Enum):
    """Actions that are recorded in the audit trail."""

    workflow_run = "workflow_run"
    workflow_create = "workflow_create"
    skill_install = "skill_install"
    skill_uninstall = "skill_uninstall"
    prompt_sync = "prompt_sync"
    prompt_promote = "prompt_promote"
    user_login = "user_login"
    user_role_change = "user_role_change"
    budget_change = "budget_change"
    human_review_decision = "human_review_decision"
    data_redacted = "data_redacted"


class AuditEntry(BaseModel):
    """Single audit log entry."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str | None = None
    team_id: str | None = None
    action: AuditAction
    resource_type: str = Field(..., description="e.g. 'workflow', 'skill', 'prompt'")
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    duration_ms: float | None = None


# ---------------------------------------------------------------------------
# Audit logger (in-memory)
# ---------------------------------------------------------------------------

class AuditLogger:
    """In-memory audit logger.

    Stores :class:`AuditEntry` records and supports filtered queries.
    Production deployments should persist entries to a database or
    external audit system.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()
        logger.info("audit_logger_initialized")

    # -- Write --------------------------------------------------------------

    def log(self, entry: AuditEntry) -> AuditEntry:
        """Record an audit entry and return it."""
        with self._lock:
            self._entries.append(entry)

        logger.info(
            "audit_logged",
            action=entry.action.value,
            user_id=entry.user_id,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
        )
        return entry

    # -- Query --------------------------------------------------------------

    def query(
        self,
        *,
        action: AuditAction | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AuditEntry]:
        """Return entries matching the supplied filters.

        All filters are optional; only non-``None`` filters are applied.
        """
        with self._lock:
            results = list(self._entries)

        if action is not None:
            results = [e for e in results if e.action == action]
        if user_id is not None:
            results = [e for e in results if e.user_id == user_id]
        if team_id is not None:
            results = [e for e in results if e.team_id == team_id]
        if resource_type is not None:
            results = [e for e in results if e.resource_type == resource_type]
        if resource_id is not None:
            results = [e for e in results if e.resource_id == resource_id]
        if start_date is not None:
            results = [e for e in results if e.timestamp >= start_date]
        if end_date is not None:
            results = [e for e in results if e.timestamp <= end_date]

        return results

    # -- Helpers ------------------------------------------------------------

    def count(self) -> int:
        """Return total number of stored entries."""
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Remove all stored entries (useful for tests)."""
        with self._lock:
            self._entries.clear()
        logger.info("audit_log_cleared")
