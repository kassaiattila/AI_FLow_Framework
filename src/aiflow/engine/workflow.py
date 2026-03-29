"""Workflow definition using DAG builder pattern.

Usage:
    @workflow(name="process-documentation", version="2.0.0", skill="process_documentation")
    def process_doc(wf: WorkflowBuilder):
        wf.step(classify_intent)
        wf.branch(on="classify_intent", when={
            "output.category == 'process'": ["elaborate"],
        }, otherwise="reject")
        wf.step(elaborate, depends_on=["classify_intent"])
        wf.step(extract, depends_on=["elaborate"])
        wf.step(review, depends_on=["extract"])
        wf.join(["generate_diagram", "generate_table"], into="assemble_output")
"""
import functools
from typing import Any, Callable

from pydantic import BaseModel

import structlog

from aiflow.engine.dag import DAG, DAGValidationError
from aiflow.engine.conditions import Condition
from aiflow.engine.step import get_step_definition, is_step

__all__ = ["workflow", "WorkflowBuilder", "WorkflowDefinition"]

logger = structlog.get_logger(__name__)


class WorkflowDefinition(BaseModel):
    """Metadata for a registered workflow."""
    name: str
    version: str = "1.0.0"
    skill: str | None = None
    complexity: str = "medium"  # small, medium, large
    description: str = ""
    tags: list[str] = []

    model_config = {"arbitrary_types_allowed": True}


class WorkflowBuilder:
    """Builder API for constructing workflow DAGs.

    Provides a fluent interface for adding steps, branches, edges, joins,
    and quality gates to a workflow.
    """

    def __init__(self) -> None:
        self._dag = DAG()
        self._step_funcs: dict[str, Callable] = {}

    @property
    def dag(self) -> DAG:
        """Access the underlying DAG."""
        return self._dag

    @property
    def step_funcs(self) -> dict[str, Callable]:
        """Map of step name -> step function."""
        return self._step_funcs

    def step(self, func: Callable, *, depends_on: list[str] | None = None,
             terminal: bool = False, max_iterations: int = 1) -> str:
        """Add a step to the workflow.

        Args:
            func: A @step-decorated function
            depends_on: List of step names this step depends on
            terminal: If True, this step ends the workflow branch
            max_iterations: Allow controlled looping (>1)

        Returns:
            The step name
        """
        step_def = get_step_definition(func)
        if step_def is None:
            # Allow plain async functions too (use function name)
            name = getattr(func, '__name__', str(func))
        else:
            name = step_def.name

        self._dag.add_node(
            name,
            step_func=func,
            is_terminal=terminal,
            max_iterations=max_iterations,
        )
        self._step_funcs[name] = func

        # Add dependency edges
        if depends_on:
            for dep in depends_on:
                self._dag.add_edge(dep, name)

        return name

    def edge(self, from_step: str, to_step: str, *,
             condition: str | None = None) -> None:
        """Add a directed edge between two steps.

        Args:
            from_step: Source step name
            to_step: Target step name
            condition: Optional condition expression (e.g., "output.score >= 8")
        """
        cond = Condition(expression=condition) if condition else None
        self._dag.add_edge(from_step, to_step, condition=cond)

    def branch(self, on: str, when: dict[str, list[str]], *,
               otherwise: str | None = None) -> None:
        """Add conditional branching from a step.

        Args:
            on: Step name whose output determines the branch
            when: Map of condition expression -> list of target step names
            otherwise: Default step if no condition matches
        """
        for condition_expr, target_steps in when.items():
            cond = Condition(expression=condition_expr, target_steps=target_steps)
            for target in target_steps:
                self._dag.add_edge(on, target, condition=cond)

        if otherwise:
            # Otherwise edge has no condition (fallback)
            self._dag.add_edge(on, otherwise)

    def join(self, steps: list[str], into: str) -> None:
        """Join multiple parallel steps into one.

        All specified steps must complete before the 'into' step runs.

        Args:
            steps: List of step names to wait for
            into: Target step name that receives all outputs
        """
        for step_name in steps:
            self._dag.add_edge(step_name, into)

    def quality_gate(self, after: str, *, gate: Any,
                     on_fail: str | None = None,
                     on_exhausted: str | None = None) -> None:
        """Add a quality gate after a step.

        Stored as metadata on the step's DAG node.

        Args:
            after: Step name to gate
            gate: QualityGate instance
            on_fail: Step to run if gate fails (e.g., "refine")
            on_exhausted: Step to run if max iterations exhausted (e.g., "human_review")
        """
        node = self._dag.get_node(after)
        node.metadata["quality_gate"] = gate
        node.metadata["quality_gate_on_fail"] = on_fail
        node.metadata["quality_gate_on_exhausted"] = on_exhausted

    def validate(self) -> list[str]:
        """Validate the workflow DAG."""
        return self._dag.validate()

    def build(self) -> DAG:
        """Build and validate the DAG. Raises DAGValidationError on issues."""
        errors = self.validate()
        if errors:
            raise DAGValidationError(errors)
        return self._dag


class Workflow:
    """A complete workflow with metadata and DAG."""

    def __init__(self, definition: WorkflowDefinition, dag: DAG,
                 step_funcs: dict[str, Callable], builder_func: Callable) -> None:
        self.definition = definition
        self.dag = dag
        self.step_funcs = step_funcs
        self._builder_func = builder_func

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def version(self) -> str:
        return self.definition.version

    def __repr__(self) -> str:
        return f"Workflow({self.name} v{self.version}, steps={self.dag.node_count})"


def workflow(
    name: str,
    *,
    version: str = "1.0.0",
    skill: str | None = None,
    complexity: str = "medium",
    description: str = "",
    tags: list[str] | None = None,
) -> Callable:
    """Decorator to define a workflow.

    The decorated function receives a WorkflowBuilder and should call
    builder methods to construct the DAG.

    Returns a Workflow instance.
    """
    def decorator(func: Callable) -> Workflow:
        definition = WorkflowDefinition(
            name=name,
            version=version,
            skill=skill,
            complexity=complexity,
            description=description,
            tags=tags or [],
        )

        builder = WorkflowBuilder()
        func(builder)

        dag = builder.build()

        wf = Workflow(
            definition=definition,
            dag=dag,
            step_funcs=builder.step_funcs,
            builder_func=func,
        )

        logger.info("workflow_defined", name=name, version=version,
                     steps=dag.node_count, edges=dag.edge_count)
        return wf

    return decorator
