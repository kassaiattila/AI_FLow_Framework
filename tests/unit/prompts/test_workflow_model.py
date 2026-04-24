"""
@test_registry:
    suite: unit-prompts
    component: aiflow.prompts.workflow (Sprint R / S139)
    covers:
        - src/aiflow/prompts/workflow.py
    phase: sprint-r-s139
    priority: high
    estimated_duration_ms: 1500
    requires_services: []
    tags: [unit, prompts, workflow, sprint-r, s139]

PromptWorkflow Pydantic model — DAG validation tests.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiflow.prompts.workflow import (
    PromptWorkflow,
    PromptWorkflowStep,
    WorkflowValidationError,
)

# Pydantic 2 wraps custom ValueError subclasses in ValidationError, but the
# original message survives — match against the wrapped form.
_ValidationErrors = (WorkflowValidationError, ValidationError)


def _step(id_: str, **kw) -> PromptWorkflowStep:
    base = {"id": id_, "prompt_name": f"prompt_for_{id_}"}
    base.update(kw)
    return PromptWorkflowStep(**base)


class TestPromptWorkflowModel:
    def test_minimal_one_step_workflow_accepts(self) -> None:
        wf = PromptWorkflow(name="wf1", version="0.1.0", steps=[_step("a")])
        assert wf.name == "wf1"
        assert wf.default_label == "prod"
        assert wf.step_ids() == ["a"]

    def test_empty_steps_rejected(self) -> None:
        with pytest.raises(_ValidationErrors, match="must not be empty"):
            PromptWorkflow(name="wf1", version="0.1.0", steps=[])

    def test_duplicate_step_id_rejected(self) -> None:
        with pytest.raises(_ValidationErrors, match="duplicate step id 'a'"):
            PromptWorkflow(
                name="wf1",
                version="0.1.0",
                steps=[_step("a"), _step("a")],
            )

    def test_unknown_dependency_rejected(self) -> None:
        with pytest.raises(_ValidationErrors, match="unknown step 'b'"):
            PromptWorkflow(
                name="wf1",
                version="0.1.0",
                steps=[_step("a", depends_on=["b"])],
            )

    def test_cycle_detected(self) -> None:
        with pytest.raises(_ValidationErrors, match="cycle"):
            PromptWorkflow(
                name="wf1",
                version="0.1.0",
                steps=[
                    _step("a", depends_on=["b"]),
                    _step("b", depends_on=["a"]),
                ],
            )

    def test_default_label_is_prod(self) -> None:
        wf = PromptWorkflow(name="wf1", version="0.1.0", steps=[_step("a")])
        assert wf.default_label == "prod"

    def test_get_step_returns_known(self) -> None:
        wf = PromptWorkflow(
            name="wf1",
            version="0.1.0",
            steps=[_step("a"), _step("b", depends_on=["a"])],
        )
        assert wf.get_step("a").id == "a"
        with pytest.raises(KeyError, match="no step with id 'missing'"):
            wf.get_step("missing")

    def test_diamond_dag_accepted(self) -> None:
        # a → b, a → c, b+c → d  (valid DAG, no cycle)
        wf = PromptWorkflow(
            name="wf_diamond",
            version="0.1.0",
            steps=[
                _step("a"),
                _step("b", depends_on=["a"]),
                _step("c", depends_on=["a"]),
                _step("d", depends_on=["b", "c"]),
            ],
        )
        assert wf.step_ids() == ["a", "b", "c", "d"]
