"""SQLAlchemy ORM models for AIFlow state persistence."""
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean, DateTime, Float, Integer, String, Text, Index,
    ForeignKey, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = ["Base", "WorkflowRunModel", "StepRunModel"]


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    type_annotation_map = {
        dict[str, Any]: JSONB,
    }


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(50), nullable=False)
    skill_name: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(100))

    trace_id: Mapped[str | None] = mapped_column(String(255))
    trace_url: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_duration_ms: Mapped[float | None] = mapped_column(Float)

    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    sla_target_seconds: Mapped[int | None] = mapped_column(Integer)
    sla_met: Mapped[bool | None] = mapped_column(Boolean)

    # team_id and user_id: plain UUID, FK added in migration 005
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    job_id: Mapped[str | None] = mapped_column(String(255))

    priority: Mapped[int] = mapped_column(Integer, default=3)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    step_runs: Mapped[list["StepRunModel"]] = relationship(back_populates="workflow_run", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'paused', 'cancelled')",
            name="chk_workflow_runs_status",
        ),
        Index("idx_wr_workflow_name", "workflow_name"),
        Index("idx_wr_status", "status"),
        Index("idx_wr_team_id", "team_id"),
        Index("idx_wr_user_id", "user_id"),
        Index("idx_wr_skill_name", "skill_name"),
        Index("idx_wr_created_at", "created_at"),
        Index("idx_wr_job_id", "job_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun {self.id} name={self.workflow_name} status={self.status}>"


class StepRunModel(Base):
    __tablename__ = "step_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )

    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(100))

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    model_used: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)

    scores: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    quality_gate_passed: Mapped[bool | None] = mapped_column(Boolean)

    checkpoint_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    checkpoint_version: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    workflow_run: Mapped["WorkflowRunModel"] = relationship(back_populates="step_runs")

    __table_args__ = (
        Index("idx_sr_workflow_run_id", "workflow_run_id"),
        Index("idx_sr_step_name", "step_name"),
        Index("idx_sr_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<StepRun {self.id} step={self.step_name} status={self.status}>"
