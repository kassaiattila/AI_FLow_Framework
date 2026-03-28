"""Score-based quality gates evaluated after agent execution.

A :class:`QualityGate` defines a named metric, a threshold, and the action to
take when the threshold is not met (retry / escalate / reject / human_review).
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

import structlog

__all__ = ["QualityGate", "QualityGateResult", "OnFailAction"]

logger = structlog.get_logger(__name__)


class OnFailAction(StrEnum):
    """What to do when a quality gate fails."""

    RETRY = "retry"
    ESCALATE = "escalate"
    REJECT = "reject"
    HUMAN_REVIEW = "human_review"


class QualityGateResult(BaseModel):
    """Outcome of evaluating a single quality gate.

    Attributes:
        passed: Whether the metric met the threshold.
        metric_value: The actual score that was checked (``-1.0`` when the
            metric is missing from the scores dict).
        gate_name: Name of the gate definition that was evaluated.
        action_taken: The ``on_fail`` action that should be taken when
            *passed* is ``False``; ``None`` when the gate passed.
    """

    passed: bool
    metric_value: float
    gate_name: str
    action_taken: str | None = None


class QualityGate(BaseModel):
    """Declarative quality gate definition.

    Attributes:
        name: Human-readable gate name (e.g. ``"accuracy_check"``).
        metric: Key to look up in the scores dictionary returned by the
            specialist (e.g. ``"accuracy"``).
        threshold: Minimum acceptable value in ``[0.0, 1.0]``.
        on_fail: Action when the score is below *threshold*.
        max_retries: How many retries are permitted when *on_fail* is
            ``retry`` (ignored for other actions).
    """

    name: str
    metric: str
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    on_fail: OnFailAction = OnFailAction.RETRY
    max_retries: int = Field(default=2, ge=0, le=10)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, scores: dict[str, float]) -> QualityGateResult:
        """Evaluate this gate against a scores dictionary.

        If the *metric* key is missing from *scores* the gate automatically
        fails with a metric value of ``-1.0``.

        Args:
            scores: Named quality scores produced by a specialist agent.

        Returns:
            A :class:`QualityGateResult` describing whether the gate passed.
        """
        metric_value = scores.get(self.metric, -1.0)
        passed = metric_value >= self.threshold

        result = QualityGateResult(
            passed=passed,
            metric_value=metric_value,
            gate_name=self.name,
            action_taken=None if passed else self.on_fail.value,
        )

        logger.debug(
            "quality_gate_evaluated",
            gate=self.name,
            metric=self.metric,
            threshold=self.threshold,
            value=metric_value,
            passed=passed,
        )
        return result
