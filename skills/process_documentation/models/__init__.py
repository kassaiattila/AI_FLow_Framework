from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "StepType",
    "Actor",
    "Decision",
    "ProcessStep",
    "ProcessExtraction",
    "ClassifyOutput",
    "ReviewOutput",
]


class StepType(StrEnum):
    start_event = "start_event"
    end_event = "end_event"
    user_task = "user_task"
    service_task = "service_task"
    exclusive_gateway = "exclusive_gateway"
    parallel_gateway = "parallel_gateway"
    inclusive_gateway = "inclusive_gateway"
    subprocess = "subprocess"


class Actor(BaseModel):
    id: str
    name: str
    role: str | None = None
    description: str | None = None


class Decision(BaseModel):
    condition: str
    yes_target: str
    no_target: str
    yes_label: str = "Igen"
    no_label: str = "Nem"


class ProcessStep(BaseModel):
    id: str
    name: str
    description: str | None = None
    step_type: StepType
    actor: str | None = None
    next_steps: list[str] = Field(default_factory=list)
    decision: Decision | None = None
    duration: str | None = None
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProcessExtraction(BaseModel):
    title: str
    description: str | None = None
    actors: list[Actor] = Field(default_factory=list)
    steps: list[ProcessStep] = Field(default_factory=list)
    start_step_id: str
    metadata: dict = Field(default_factory=dict)

    def validate_connections(self) -> list[str]:
        valid_ids = {step.id for step in self.steps}
        errors: list[str] = []
        for step in self.steps:
            for next_id in step.next_steps:
                if next_id not in valid_ids:
                    errors.append(
                        f"Step '{step.id}' references unknown next_step '{next_id}'"
                    )
        return errors


class ClassifyOutput(BaseModel):
    category: Literal["process", "question", "clarification", "reject"]
    confidence: float
    reasoning: str = ""


class ReviewOutput(BaseModel):
    score: int = Field(ge=1, le=10)
    is_acceptable: bool
    completeness_score: int = Field(ge=1, le=10)
    logic_score: int = Field(ge=1, le=10)
    actors_score: int = Field(ge=1, le=10)
    decisions_score: int = Field(ge=1, le=10)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    reasoning: str = ""
