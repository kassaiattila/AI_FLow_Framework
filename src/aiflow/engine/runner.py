"""WorkflowRunner - executes a workflow DAG, managing state and checkpoints.

This is the local execution engine. For distributed execution (via arq queue),
see src/aiflow/execution/worker.py (Phase 5).
"""
import time
from typing import Any

import structlog

from aiflow.core.context import ExecutionContext
from aiflow.core.errors import BudgetExceededError
from aiflow.core.types import Status, StepResult, StepStatus, WorkflowResult
from aiflow.engine.checkpoint import Checkpoint, CheckpointManager
from aiflow.engine.dag import DAG

__all__ = ["WorkflowRunner", "RunContext"]

logger = structlog.get_logger(__name__)


class RunContext:
    """Tracks state during a single workflow execution."""

    def __init__(self, workflow_name: str, ctx: ExecutionContext) -> None:
        self.workflow_name = workflow_name
        self.ctx = ctx
        self.completed_steps: set[str] = set()
        self.step_outputs: dict[str, Any] = {}
        self.step_results: list[StepResult] = []
        self.total_cost_usd: float = 0.0
        self.iteration_counts: dict[str, int] = {}


class WorkflowRunner:
    """Executes workflow DAGs locally (sync, in-process).

    Execution loop:
    1. Get topologically sorted step order
    2. For each ready step:
       a. Check budget
       b. Execute step (with retry policy)
       c. Record result + checkpoint
       d. Evaluate conditions for next steps
    3. On success: return completed result
    4. On failure: return error result
    """

    def __init__(
        self,
        checkpoint_manager: CheckpointManager | None = None,
        models: Any | None = None,
        prompts: Any | None = None,
    ) -> None:
        self._checkpoint_mgr = checkpoint_manager or CheckpointManager()
        self._models = models
        self._prompts = prompts

    async def run(
        self,
        workflow_name: str,
        dag: DAG,
        step_funcs: dict[str, Any],
        input_data: dict[str, Any],
        *,
        ctx: ExecutionContext | None = None,
    ) -> WorkflowResult:
        """Execute a workflow from start to finish.

        Args:
            workflow_name: Name of the workflow
            dag: The workflow DAG
            step_funcs: Map of step name -> callable
            input_data: Initial input data
            ctx: Execution context (created if not provided)

        Returns:
            WorkflowResult with status, output, cost, etc.
        """
        ctx = ctx or ExecutionContext()
        run_ctx = RunContext(workflow_name=workflow_name, ctx=ctx)
        start_time = time.monotonic()

        logger.info("workflow_started", workflow=workflow_name, run_id=ctx.run_id)

        try:
            # Get execution order
            sorted_steps = dag.topological_sort()
            total_steps = len(sorted_steps)

            # Execute steps in order
            last_output: dict[str, Any] | None = None

            for step_name in sorted_steps:
                # Check if step should run (predecessors completed + conditions met)
                if not self._should_execute(step_name, dag, run_ctx):
                    continue

                # Check budget
                if ctx.budget_remaining_usd <= 0:
                    raise BudgetExceededError(
                        f"Budget exhausted before step '{step_name}'",
                        details={"remaining": ctx.budget_remaining_usd},
                    )

                # Get step function
                step_func = step_funcs.get(step_name)
                if step_func is None:
                    logger.warning("step_func_missing", step=step_name)
                    continue

                # Prepare input (output of predecessors or initial input)
                step_input = self._prepare_step_input(step_name, dag, run_ctx, input_data)

                # Execute step
                step_result = await self._execute_step(
                    step_name, step_func, step_input, ctx
                )

                # Record result
                run_ctx.completed_steps.add(step_name)
                run_ctx.step_outputs[step_name] = step_result.output_data
                run_ctx.step_results.append(step_result)
                run_ctx.total_cost_usd += step_result.cost_usd

                # Update budget
                ctx = ctx.with_budget_decrease(step_result.cost_usd)

                # Save checkpoint
                checkpoint = Checkpoint(
                    workflow_run_id=ctx.run_id,
                    step_name=step_name,
                    step_index=len(run_ctx.completed_steps),
                    version=len(run_ctx.completed_steps),
                    completed_steps=list(run_ctx.completed_steps),
                    step_outputs=run_ctx.step_outputs,
                    accumulated_cost_usd=run_ctx.total_cost_usd,
                )
                self._checkpoint_mgr.save(checkpoint)

                last_output = step_result.output_data

            # Workflow completed
            duration = (time.monotonic() - start_time) * 1000
            logger.info("workflow_completed", workflow=workflow_name,
                        run_id=ctx.run_id, duration_ms=round(duration, 1),
                        cost_usd=run_ctx.total_cost_usd,
                        steps_completed=len(run_ctx.completed_steps))

            return WorkflowResult(
                status=Status.COMPLETED,
                output_data=last_output,
                total_duration_ms=duration,
                total_cost_usd=run_ctx.total_cost_usd,
                steps_completed=len(run_ctx.completed_steps),
                steps_total=total_steps,
            )

        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            logger.error("workflow_failed", workflow=workflow_name,
                         run_id=ctx.run_id, error=str(e),
                         error_type=type(e).__name__,
                         steps_completed=len(run_ctx.completed_steps))

            return WorkflowResult(
                status=Status.FAILED,
                error=str(e),
                total_duration_ms=duration,
                total_cost_usd=run_ctx.total_cost_usd,
                steps_completed=len(run_ctx.completed_steps),
                steps_total=dag.node_count,
            )

    async def resume(
        self,
        workflow_name: str,
        dag: DAG,
        step_funcs: dict[str, Any],
        run_id: str,
        input_data: dict[str, Any],
    ) -> WorkflowResult:
        """Resume a workflow from the last checkpoint."""
        checkpoint = self._checkpoint_mgr.get_latest(run_id)
        if checkpoint is None:
            logger.warning("no_checkpoint_found", run_id=run_id)
            # Start from scratch
            return await self.run(workflow_name, dag, step_funcs, input_data)

        logger.info("workflow_resuming", run_id=run_id,
                     from_step=checkpoint.step_name,
                     completed=checkpoint.completed_steps)

        ctx = ExecutionContext(
            run_id=run_id,
            checkpoint_data=checkpoint.to_dict(),
            checkpoint_version=checkpoint.version,
        )
        # Re-run with already-completed steps skipped
        return await self.run(workflow_name, dag, step_funcs, input_data, ctx=ctx)

    def _should_execute(self, step_name: str, dag: DAG, run_ctx: RunContext) -> bool:
        """Check if a step should execute based on predecessors and conditions."""
        # Already completed (resume case)?
        if step_name in run_ctx.completed_steps:
            return False

        # Check from checkpoint (resume case)
        if run_ctx.ctx.checkpoint_data:
            completed_in_checkpoint = run_ctx.ctx.checkpoint_data.get("completed_steps", [])
            if step_name in completed_in_checkpoint:
                # Restore output from checkpoint
                outputs = run_ctx.ctx.checkpoint_data.get("step_outputs", {})
                if step_name in outputs:
                    run_ctx.step_outputs[step_name] = outputs[step_name]
                    run_ctx.completed_steps.add(step_name)
                return False

        # All predecessors must be completed
        predecessors = dag.get_predecessors(step_name)
        if predecessors and not all(p in run_ctx.completed_steps for p in predecessors):
            return False

        # Check conditions on incoming edges
        edges = [e for e in dag._edges if e.to_node == step_name and e.condition]
        if edges:
            # At least one conditional edge must be satisfied
            for edge in edges:
                source_output = run_ctx.step_outputs.get(edge.from_node, {})
                if source_output and edge.condition and edge.condition.evaluate(source_output):
                    return True
            # If there are only conditional edges and none matched, skip
            unconditional = [e for e in dag._edges if e.to_node == step_name and not e.condition]
            if not unconditional:
                return False

        return True

    def _prepare_step_input(self, step_name: str, dag: DAG,
                            run_ctx: RunContext, initial_input: dict) -> Any:
        """Prepare input data for a step."""
        predecessors = dag.get_predecessors(step_name)
        if not predecessors:
            return initial_input

        # Single predecessor: pass its output
        if len(predecessors) == 1:
            return run_ctx.step_outputs.get(predecessors[0], initial_input)

        # Multiple predecessors (join): merge outputs
        merged = {}
        for pred in predecessors:
            output = run_ctx.step_outputs.get(pred, {})
            if isinstance(output, dict):
                merged.update(output)
            else:
                merged[pred] = output
        return merged

    async def _execute_step(self, step_name: str, step_func: Any,
                            input_data: Any, ctx: ExecutionContext) -> StepResult:
        """Execute a single step with optional service injection.

        If the step function accepts keyword arguments (models, prompts, ctx),
        they are injected automatically. Otherwise, only input_data is passed
        (backward compatible with existing steps).
        """
        import inspect

        start = time.monotonic()

        try:
            # Inspect function signature to determine injection
            sig = inspect.signature(step_func)
            kwargs: dict[str, Any] = {}

            # Check for service parameters (keyword-only or regular)
            params = sig.parameters
            if "models" in params and self._models is not None:
                kwargs["models"] = self._models
            if "prompts" in params and self._prompts is not None:
                kwargs["prompts"] = self._prompts
            if "ctx" in params:
                kwargs["ctx"] = ctx

            if kwargs:
                output = await step_func(input_data, **kwargs)
            else:
                output = await step_func(input_data)

            duration = (time.monotonic() - start) * 1000
            return StepResult(
                status=StepStatus.COMPLETED,
                output_data=output if isinstance(output, dict) else {"result": output},
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error("step_execution_error", step=step_name,
                         error=str(e), error_type=type(e).__name__)
            raise
