"""Request-scoped execution context that flows through every component."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

__all__ = ["ExecutionContext", "TraceContext"]


class TraceContext(BaseModel):
    """Tracing information for Langfuse + OpenTelemetry."""

    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    span_id: str | None = None
    langfuse_trace_id: str | None = None
    langfuse_trace_url: str | None = None


class ExecutionContext(BaseModel):
    """Request-scoped context flowing through every AIFlow component."""

    # Identity
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_context: TraceContext = Field(default_factory=TraceContext)

    # Scoping
    team_id: str | None = None
    user_id: str | None = None

    # Instance context (Phase A - Modular Deployment)
    instance_id: str | None = None
    instance_name: str | None = None
    customer: str | None = None
    prompt_namespace: str | None = None

    # Runtime configuration
    prompt_label: str = "prod"
    model_override: str | None = None
    budget_remaining_usd: float = 10.0

    # Checkpoint (for resume from failure)
    checkpoint_data: dict[str, Any] | None = None
    checkpoint_version: int = 0

    # Flags
    dry_run: bool = False

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def with_budget_decrease(self, cost: float) -> "ExecutionContext":
        """Return new context with decreased budget."""
        return self.model_copy(update={"budget_remaining_usd": self.budget_remaining_usd - cost})

    def with_checkpoint(self, data: dict[str, Any]) -> "ExecutionContext":
        """Return new context with updated checkpoint."""
        return self.model_copy(
            update={
                "checkpoint_data": data,
                "checkpoint_version": self.checkpoint_version + 1,
            }
        )
