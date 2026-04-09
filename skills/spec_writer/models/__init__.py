"""Pydantic I/O models for the Spec Writer skill."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "SpecInput",
    "SpecRequirement",
    "SpecDraft",
    "SpecReview",
    "SpecOutput",
]


SpecType = Literal["feature", "api", "db", "user_story"]
SpecLanguage = Literal["hu", "en"]


class SpecInput(BaseModel):
    """Raw user request for a specification."""

    raw_text: str = Field(..., description="Free-form description of what to spec out")
    spec_type: SpecType = "feature"
    language: SpecLanguage = "hu"
    context: str | None = Field(
        default=None,
        description="Optional additional context (existing system, constraints, etc.)",
    )


class SpecField(BaseModel):
    """A single input or output field with type + description."""

    name: str
    type: str = "string"
    description: str = ""


class SpecRequirement(BaseModel):
    """Structured requirement extracted by the analyzer."""

    title: str
    description: str = ""
    actors: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    inputs: list[SpecField] = Field(default_factory=list)
    outputs: list[SpecField] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)


class SpecDraft(BaseModel):
    """Markdown spec draft produced by the generator."""

    title: str
    spec_type: SpecType
    language: SpecLanguage
    markdown: str
    sections_count: int = 0
    word_count: int = 0


class SpecReview(BaseModel):
    """Quality review of a spec draft."""

    is_acceptable: bool = False
    score: float = 0.0  # 0.0 .. 10.0
    missing_sections: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class SpecOutput(BaseModel):
    """Final spec output bundle returned by the workflow."""

    requirement: SpecRequirement
    draft: SpecDraft
    review: SpecReview
    final_markdown: str
