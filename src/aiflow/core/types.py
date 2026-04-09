"""Common type definitions for AIFlow."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel

__all__ = ["Status", "StepStatus", "Priority", "SkillType", "StepResult", "WorkflowResult"]


class Status(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class SkillType(StrEnum):
    AI = "ai"
    RPA = "rpa"
    HYBRID = "hybrid"


class StepResult(BaseModel):
    status: StepStatus
    output_data: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None
    duration_ms: float | None = None
    cost_usd: float = 0.0
    scores: dict[str, float] = {}


class WorkflowResult(BaseModel):
    status: Status
    output_data: dict[str, Any] | None = None
    error: str | None = None
    total_duration_ms: float | None = None
    total_cost_usd: float = 0.0
    steps_completed: int = 0
    steps_total: int = 0
