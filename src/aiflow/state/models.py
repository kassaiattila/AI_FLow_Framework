"""SQLAlchemy ORM models for AIFlow state persistence."""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "Base",
    "PipelineDefinitionModel",
    "WorkflowRunModel",
    "StepRunModel",
    "SkillInstanceModel",
    "EmailConnectorConfigModel",
    "EmailFetchHistoryModel",
]


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

    # Instance FK (migration 012)
    instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill_instances.id", ondelete="SET NULL")
    )

    # Pipeline FK (migration 027)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_definitions.id", ondelete="SET NULL")
    )

    priority: Mapped[int] = mapped_column(Integer, default=3)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    step_runs: Mapped[list["StepRunModel"]] = relationship(back_populates="workflow_run", cascade="all, delete-orphan")
    instance: Mapped["SkillInstanceModel | None"] = relationship(back_populates="workflow_runs")
    pipeline: Mapped["PipelineDefinitionModel | None"] = relationship(back_populates="workflow_runs")

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
        Index("idx_wr_instance_id", "instance_id"),
        Index("idx_wr_pipeline_id", "pipeline_id"),
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


class SkillInstanceModel(Base):
    """Configured deployment of a skill template for a specific customer."""

    __tablename__ = "skill_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer: Mapped[str] = mapped_column(String(100), nullable=False)

    skill_name: Mapped[str] = mapped_column(
        String(255), ForeignKey("skills.name"), nullable=False
    )
    skill_version: Mapped[str] = mapped_column(String(50), nullable=False)

    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    prompt_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_label: Mapped[str] = mapped_column(String(50), default="prod")

    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    fallback_model: Mapped[str | None] = mapped_column(String(100))

    budget_monthly_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    budget_used_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    budget_per_run_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    budget_reset_day: Mapped[int] = mapped_column(Integer, default=1)

    sla_target_seconds: Mapped[int | None] = mapped_column(Integer)
    sla_p95_target_seconds: Mapped[int | None] = mapped_column(Integer)

    input_channel: Mapped[str] = mapped_column(String(50), default="api")
    output_channel: Mapped[str] = mapped_column(String(50), default="api")
    queue_name: Mapped[str | None] = mapped_column(String(255))

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    created_by: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    workflow_runs: Mapped[list["WorkflowRunModel"]] = relationship(back_populates="instance")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'paused', 'deprecated', 'error')",
            name="chk_si_status",
        ),
        CheckConstraint(
            "input_channel IN ('api', 'email', 'webhook', 'queue')",
            name="chk_si_input",
        ),
        CheckConstraint(
            "output_channel IN ('api', 'email', 'webhook', 'db')",
            name="chk_si_output",
        ),
        Index("idx_si_customer", "customer"),
        Index("idx_si_skill_name", "skill_name"),
        Index("idx_si_status", "status"),
        Index("idx_si_customer_skill", "customer", "skill_name"),
        Index("idx_si_prompt_namespace", "prompt_namespace"),
    )

    def __repr__(self) -> str:
        return f"<SkillInstance {self.instance_name} customer={self.customer} status={self.status}>"


class EmailConnectorConfigModel(Base):
    """Email connector configuration (IMAP, O365/Graph, Gmail)."""

    __tablename__ = "email_connector_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    host: Mapped[str | None] = mapped_column(String(255))
    port: Mapped[int | None] = mapped_column(Integer)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    mailbox: Mapped[str | None] = mapped_column(String(255))
    credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    polling_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    max_emails_per_fetch: Mapped[int] = mapped_column(Integer, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    fetch_history: Mapped[list["EmailFetchHistoryModel"]] = relationship(
        back_populates="config", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "provider IN ('imap', 'o365_graph', 'gmail')",
            name="chk_ecc_provider",
        ),
        Index("idx_ecc_provider", "provider"),
        Index("idx_ecc_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<EmailConnectorConfig {self.name} provider={self.provider} active={self.is_active}>"


class EmailFetchHistoryModel(Base):
    """Tracks each email fetch operation per connector."""

    __tablename__ = "email_fetch_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_connector_configs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    email_count: Mapped[int] = mapped_column(Integer, default=0)
    new_emails: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    config: Mapped["EmailConnectorConfigModel"] = relationship(back_populates="fetch_history")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="chk_efh_status",
        ),
        Index("idx_efh_config_id", "config_id"),
        Index("idx_efh_fetched_at", "fetched_at"),
        Index("idx_efh_status", "status"),
    )


class PipelineDefinitionModel(Base):
    """YAML-defined pipeline stored with compiled definition (migration 027)."""

    __tablename__ = "pipeline_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0.0"
    )
    description: Mapped[str | None] = mapped_column(Text)

    yaml_source: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trigger_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict
    )
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict
    )

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    workflow_runs: Mapped[list["WorkflowRunModel"]] = relationship(
        back_populates="pipeline"
    )

    __table_args__ = (
        Index("idx_pd_name", "name"),
        Index("idx_pd_enabled", "enabled"),
        Index("idx_pd_team_id", "team_id"),
    )
