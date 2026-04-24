"""PromptWorkflow — descriptor-only model for composing multiple prompt steps.

Sprint R / S139: introduces the contract used by S140 (admin UI) and
S141 (skill migration). This module **does not execute** anything; it
just declares a multi-step prompt plan with dependencies, gating
metadata, and a Langfuse default label.

A workflow is a DAG of steps. Each step references a prompt by name
(resolved later via :class:`aiflow.prompts.manager.PromptManager`) and
may declare ``depends_on`` predecessors. Cycles are rejected at
validation time via Kahn's algorithm.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

__all__ = [
    "PromptWorkflow",
    "PromptWorkflowStep",
    "WorkflowValidationError",
]


class WorkflowValidationError(ValueError):
    """Raised when a PromptWorkflow fails structural validation."""


class PromptWorkflowStep(BaseModel):
    """One step inside a :class:`PromptWorkflow`.

    Fields:
        id: Stable identifier within the workflow (referenced by other
            steps via ``depends_on``).
        prompt_name: Name passed to ``PromptManager.get(...)`` to fetch
            the actual prompt definition.
        description: Free-form human description.
        required: When ``False`` the step may be skipped at execution
            time (executor lands S141).
        depends_on: Step ids that must complete before this one runs.
        output_key: Hint for the executor on where to merge this step's
            output in the final payload (e.g.,
            ``"extracted_fields.header"``).
        metadata: Arbitrary key-value bag for executor hints
            (cost ceiling, gate condition, langfuse variant, ...).
    """

    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    prompt_name: str = Field(min_length=1)
    description: str | None = None
    required: bool = True
    depends_on: list[str] = Field(default_factory=list)
    output_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptWorkflow(BaseModel):
    """A named, versioned, DAG-structured composition of prompt steps.

    Validation rejects:
      * empty ``steps``
      * duplicate step ids
      * ``depends_on`` referencing an unknown step
      * cycles in the dependency graph (Kahn topological sort)
    """

    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str | None = None
    steps: list[PromptWorkflowStep]
    tags: list[str] = Field(default_factory=list)
    default_label: str = "prod"

    @model_validator(mode="after")
    def _validate_dag(self) -> PromptWorkflow:
        if not self.steps:
            raise WorkflowValidationError(f"workflow {self.name!r}: steps must not be empty")

        seen: set[str] = set()
        for step in self.steps:
            if step.id in seen:
                raise WorkflowValidationError(
                    f"workflow {self.name!r}: duplicate step id {step.id!r}"
                )
            seen.add(step.id)

        for step in self.steps:
            for dep in step.depends_on:
                if dep not in seen:
                    raise WorkflowValidationError(
                        f"workflow {self.name!r}: step {step.id!r} depends on unknown step {dep!r}"
                    )

        # Kahn topological sort to detect cycles
        indegree: dict[str, int] = {s.id: 0 for s in self.steps}
        adj: dict[str, list[str]] = {s.id: [] for s in self.steps}
        for s in self.steps:
            for dep in s.depends_on:
                adj[dep].append(s.id)
                indegree[s.id] += 1

        queue = [sid for sid, deg in indegree.items() if deg == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for nxt in adj[current]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if visited != len(self.steps):
            raise WorkflowValidationError(
                f"workflow {self.name!r}: dependency graph contains a cycle"
            )

        return self

    def step_ids(self) -> list[str]:
        """Return all step ids in declaration order."""
        return [s.id for s in self.steps]

    def get_step(self, step_id: str) -> PromptWorkflowStep:
        """Look up a step by id; raises ``KeyError`` if absent."""
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(f"workflow {self.name!r}: no step with id {step_id!r}")
