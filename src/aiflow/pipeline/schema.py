"""Pipeline YAML schema — Pydantic models for pipeline definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "PipelineDefinition",
    "PipelineStepDef",
    "PipelineTriggerDef",
    "StepRetryPolicy",
    "TriggerType",
]


class TriggerType(str, Enum):
    """Supported pipeline trigger types."""

    MANUAL = "manual"
    CRON = "cron"
    EVENT = "event"
    WEBHOOK = "webhook"


class PipelineTriggerDef(BaseModel):
    """Pipeline trigger configuration."""

    type: TriggerType = TriggerType.MANUAL
    cron_expression: str | None = Field(
        None, description="Cron expression (for type=cron)"
    )
    event_type: str | None = Field(
        None, description="Event type name (for type=event)"
    )
    webhook_path: str | None = Field(
        None, description="Webhook URL path (for type=webhook)"
    )


class StepRetryPolicy(BaseModel):
    """Retry policy for a pipeline step (maps to engine RetryPolicy)."""

    max_retries: int = Field(3, ge=0, le=10)
    backoff_base: float = Field(1.0, ge=0.1)
    backoff_max: float = Field(60.0, ge=1.0)


class PipelineStepDef(BaseModel):
    """Definition of a single step in a pipeline."""

    name: str = Field(..., description="Unique step identifier within pipeline")
    service: str = Field(..., description="Service name in adapter registry")
    method: str = Field(..., description="Service method to call")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Step config (values can contain Jinja2 templates)",
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Names of prerequisite steps"
    )
    for_each: str | None = Field(
        None, description="Jinja2 expression that evaluates to a list"
    )
    condition: str | None = Field(
        None, description="Condition: 'output.field op value'"
    )
    retry: StepRetryPolicy | None = Field(
        None, description="Retry policy for this step"
    )
    timeout: int | None = Field(None, description="Timeout in seconds", ge=1)
    concurrency: int = Field(
        5, description="Max parallel iterations for for_each", ge=1, le=100
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Step name cannot be empty")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Step name must be alphanumeric with _ or -: '{v}'"
            )
        return v


class PipelineDefinition(BaseModel):
    """Complete pipeline definition — parsed from YAML."""

    name: str = Field(..., description="Unique pipeline identifier")
    version: str = Field("1.0.0", description="Semantic version")
    description: str = Field("", description="Human-readable description")
    trigger: PipelineTriggerDef = Field(default_factory=PipelineTriggerDef)
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="Input parameter schema"
    )
    steps: list[PipelineStepDef] = Field(
        ..., min_length=1, description="Pipeline steps"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_pipeline_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Pipeline name cannot be empty")
        return v

    @field_validator("steps")
    @classmethod
    def validate_unique_step_names(
        cls, steps: list[PipelineStepDef],
    ) -> list[PipelineStepDef]:
        names = [s.name for s in steps]
        dupes = [n for n in names if names.count(n) > 1]
        if dupes:
            raise ValueError(f"Duplicate step names: {set(dupes)}")
        return steps

    def get_step(self, name: str) -> PipelineStepDef | None:
        """Get a step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None

    def step_names(self) -> list[str]:
        """Return all step names in order."""
        return [s.name for s in self.steps]
