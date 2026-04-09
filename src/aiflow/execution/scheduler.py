"""Workflow scheduler with cron, event, webhook, and manual triggers."""

from __future__ import annotations

import enum
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "TriggerType",
    "ScheduleDefinition",
    "CronTrigger",
    "Scheduler",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums & models
# ---------------------------------------------------------------------------


class TriggerType(str, enum.Enum):
    """Supported trigger types for scheduled workflows."""

    cron = "cron"
    event = "event"
    webhook = "webhook"
    manual = "manual"


class ScheduleDefinition(BaseModel):
    """Defines a scheduled workflow trigger."""

    name: str = Field(..., description="Unique schedule name")
    workflow_name: str = Field(..., description="Workflow to execute")
    trigger_type: TriggerType = Field(..., description="How the workflow is triggered")

    # Cron-specific
    cron_expression: str | None = Field(
        None,
        description="Simplified cron expression: 'minute hour day_of_month month day_of_week'",
    )

    # Event-specific
    event_pattern: str | None = Field(None, description="Event name/pattern to subscribe to")

    # Webhook-specific
    webhook_path: str | None = Field(None, description="HTTP path that triggers the workflow")

    # Execution settings
    input_data: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10)
    enabled: bool = True
    team_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Simple cron pattern matcher
# ---------------------------------------------------------------------------


class CronTrigger:
    """Evaluate whether a simplified cron expression should fire at a given time.

    Supports: ``minute hour day_of_month month day_of_week``
    Each field accepts a literal integer or ``*`` (wildcard).  Ranges and
    step values are **not** implemented -- this is a minimal scheduler.
    """

    _FIELDS = ("minute", "hour", "day", "month", "weekday")

    def __init__(self, expression: str) -> None:
        self._expression = expression.strip()
        parts = self._expression.split()
        if len(parts) != 5:
            raise ValueError(
                f"Cron expression must have 5 fields, got {len(parts)}: {expression!r}"
            )
        self._parts = parts

    @property
    def expression(self) -> str:
        return self._expression

    # ------------------------------------------------------------------

    def _match_field(self, field_value: str, actual: int) -> bool:
        """Return True if *field_value* matches *actual*."""
        if field_value == "*":
            return True
        # Support comma-separated values: "0,15,30,45"
        for token in field_value.split(","):
            token = token.strip()
            if token.isdigit() and int(token) == actual:
                return True
        return False

    def should_fire(self, now: datetime | None = None) -> bool:
        """Return True when *now* matches the cron expression."""
        if now is None:
            now = datetime.now(UTC)

        actuals = (
            now.minute,
            now.hour,
            now.day,
            now.month,
            now.isoweekday() % 7,  # 0=Sun .. 6=Sat
        )

        for field_val, actual in zip(self._parts, actuals, strict=False):
            if not self._match_field(field_val, actual):
                return False
        return True

    def __repr__(self) -> str:
        return f"CronTrigger({self._expression!r})"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class Scheduler:
    """In-memory schedule manager.

    Stores :class:`ScheduleDefinition` objects and exposes CRUD plus
    enable/disable helpers.  The actual tick loop (checking cron triggers,
    dispatching jobs) is left to the caller or a background task.
    """

    def __init__(self) -> None:
        self._schedules: dict[str, ScheduleDefinition] = {}
        self._cron_triggers: dict[str, CronTrigger] = {}
        self._lock = threading.Lock()
        logger.info("scheduler_initialized")

    # -- CRUD ---------------------------------------------------------------

    def add_schedule(self, definition: ScheduleDefinition) -> None:
        """Register a new schedule."""
        with self._lock:
            if definition.name in self._schedules:
                raise ValueError(f"Schedule already exists: {definition.name!r}")
            self._schedules[definition.name] = definition

            if definition.trigger_type == TriggerType.cron and definition.cron_expression:
                self._cron_triggers[definition.name] = CronTrigger(definition.cron_expression)

        logger.info(
            "schedule_added",
            name=definition.name,
            workflow=definition.workflow_name,
            trigger=definition.trigger_type.value,
        )

    def remove_schedule(self, name: str) -> None:
        """Remove a schedule by name."""
        with self._lock:
            if name not in self._schedules:
                raise KeyError(f"Schedule not found: {name!r}")
            del self._schedules[name]
            self._cron_triggers.pop(name, None)
        logger.info("schedule_removed", name=name)

    def get_schedule(self, name: str) -> ScheduleDefinition:
        """Return a schedule by name."""
        with self._lock:
            if name not in self._schedules:
                raise KeyError(f"Schedule not found: {name!r}")
            return self._schedules[name]

    def list_schedules(self) -> list[ScheduleDefinition]:
        """Return all registered schedules."""
        with self._lock:
            return list(self._schedules.values())

    # -- Enable / disable --------------------------------------------------

    def enable_schedule(self, name: str) -> None:
        """Enable a previously disabled schedule."""
        with self._lock:
            sched = self._schedules.get(name)
            if sched is None:
                raise KeyError(f"Schedule not found: {name!r}")
            sched.enabled = True
        logger.info("schedule_enabled", name=name)

    def disable_schedule(self, name: str) -> None:
        """Disable a schedule without removing it."""
        with self._lock:
            sched = self._schedules.get(name)
            if sched is None:
                raise KeyError(f"Schedule not found: {name!r}")
            sched.enabled = False
        logger.info("schedule_disabled", name=name)

    # -- Tick ---------------------------------------------------------------

    def get_due_schedules(self, now: datetime | None = None) -> list[ScheduleDefinition]:
        """Return all cron schedules that should fire at *now*."""
        if now is None:
            now = datetime.now(UTC)

        due: list[ScheduleDefinition] = []
        with self._lock:
            for name, trigger in self._cron_triggers.items():
                sched = self._schedules[name]
                if sched.enabled and trigger.should_fire(now):
                    due.append(sched)
        if due:
            logger.info("due_schedules_found", count=len(due))
        return due

    @property
    def count(self) -> int:
        """Return total number of registered schedules."""
        with self._lock:
            return len(self._schedules)
