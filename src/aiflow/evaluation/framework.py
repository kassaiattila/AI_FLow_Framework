"""EvalSuite and EvalCase for running evaluation pipelines.

Supports both sync step functions and workflow callables.
Produces EvalResult objects with scores, timing, and cost tracking.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["EvalCase", "EvalResult", "EvalSuite", "EvalSummary"]

logger = structlog.get_logger(__name__)


class EvalCase(BaseModel):
    """A single evaluation test case."""

    name: str
    input_data: dict[str, Any]
    expected_output: Any = None
    assertions: list[str] = Field(default_factory=list)
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    priority: str = "normal"


class EvalResult(BaseModel):
    """Result of running one EvalCase."""

    case_name: str
    passed: bool
    actual_output: Any = None
    scores: dict[str, float] = Field(default_factory=dict)
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None


class EvalSummary(BaseModel):
    """Summary statistics for an evaluation run."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    error_count: int = 0
    pass_rate: float = 0.0
    total_duration_ms: float = 0.0
    total_cost_usd: float = 0.0
    avg_duration_ms: float = 0.0


class EvalSuite:
    """Runs a collection of EvalCases against a step function or workflow.

    The step_func receives input_data (dict) and returns the actual output.
    Assertions in each case are matched against built-in scorers.
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name

    def run(
        self,
        cases: list[EvalCase],
        step_func: Callable[[dict[str, Any]], Any],
        scorers: dict[str, Callable[..., tuple[float, bool]]] | None = None,
    ) -> list[EvalResult]:
        """Run all evaluation cases through the step function.

        Args:
            cases: List of EvalCase instances.
            step_func: Callable that receives input_data and returns output.
            scorers: Optional mapping of assertion name -> scorer function.
                     Each scorer receives (actual_output, expected_output, **kwargs)
                     and returns (score: float, passed: bool).

        Returns:
            List of EvalResult, one per case.
        """
        results: list[EvalResult] = []
        scorers = scorers or {}

        for case in cases:
            result = self._run_single(case, step_func, scorers)
            results.append(result)

        logger.info(
            "eval_suite_completed",
            suite=self.name,
            total=len(results),
            passed=sum(1 for r in results if r.passed),
        )
        return results

    def _run_single(
        self,
        case: EvalCase,
        step_func: Callable[[dict[str, Any]], Any],
        scorers: dict[str, Callable[..., tuple[float, bool]]],
    ) -> EvalResult:
        """Run a single evaluation case."""
        start = time.perf_counter()
        try:
            actual_output = step_func(case.input_data)
            duration_ms = (time.perf_counter() - start) * 1000

            # Run assertions via scorers
            all_passed = True
            scores: dict[str, float] = {}

            for assertion in case.assertions:
                if assertion in scorers:
                    score, passed = scorers[assertion](actual_output, case.expected_output)
                    scores[assertion] = score
                    if not passed:
                        all_passed = False
                else:
                    # Default: check equality if expected_output is set
                    if case.expected_output is not None:
                        eq = actual_output == case.expected_output
                        scores[assertion] = 1.0 if eq else 0.0
                        if not eq:
                            all_passed = False

            # If no assertions, pass if no error
            if not case.assertions:
                all_passed = True

            return EvalResult(
                case_name=case.name,
                passed=all_passed,
                actual_output=actual_output,
                scores=scores,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return EvalResult(
                case_name=case.name,
                passed=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

    @staticmethod
    def summary(results: list[EvalResult]) -> EvalSummary:
        """Compute summary statistics from evaluation results.

        Args:
            results: List of EvalResult objects.

        Returns:
            EvalSummary with aggregate stats.
        """
        if not results:
            return EvalSummary()

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        error_count = sum(1 for r in results if r.error is not None)
        total_duration = sum(r.duration_ms for r in results)
        total_cost = sum(r.cost_usd for r in results)

        return EvalSummary(
            total=total,
            passed=passed,
            failed=failed,
            error_count=error_count,
            pass_rate=passed / total if total > 0 else 0.0,
            total_duration_ms=total_duration,
            total_cost_usd=total_cost,
            avg_duration_ms=total_duration / total if total > 0 else 0.0,
        )
