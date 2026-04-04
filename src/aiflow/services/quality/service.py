"""LLM quality evaluation and cost estimation service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "CostEstimate",
    "QualityConfig",
    "QualityOverview",
    "QualityService",
    "RubricResult",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RubricResult(BaseModel):
    """Result of a rubric-based quality evaluation."""

    score: float = Field(..., ge=0.0, le=1.0, description="Quality score from 0.0 to 1.0")
    pass_: bool = Field(..., description="Whether the evaluation passed")
    reasoning: str = Field("", description="Explanation of the score")
    rubric: str = Field("", description="Rubric that was evaluated")
    model: str = Field("", description="Model used for evaluation")
    evaluated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class QualityOverview(BaseModel):
    """Aggregated quality metrics overview."""

    total_evaluations: int = 0
    avg_score: float = 0.0
    pass_rate: float = 0.0
    cost_today: float = 0.0
    cost_month: float = 0.0


class CostEstimate(BaseModel):
    """Estimated cost for a pipeline or operation."""

    estimated_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model: str = ""


class QualityConfig(ServiceConfig):
    """Quality service configuration."""

    default_model: str = "gpt-4o-mini"
    pass_threshold: float = 0.7


# ---------------------------------------------------------------------------
# Built-in rubrics
# ---------------------------------------------------------------------------

BUILTIN_RUBRICS: dict[str, str] = {
    "relevance": (
        "Score how relevant the response is to the question or prompt. "
        "5 = directly answers the question with specific detail, "
        "1 = completely off-topic or unrelated."
    ),
    "faithfulness": (
        "Score how faithful the response is to the provided context. "
        "5 = every claim is grounded in the context, "
        "1 = contains fabricated or contradicted information."
    ),
    "completeness": (
        "Score how complete the response is. "
        "5 = covers all key aspects with nothing missing, "
        "1 = misses most important points."
    ),
    "extraction_accuracy": (
        "Score how accurately entities and data were extracted. "
        "5 = all fields correct with right types and values, "
        "1 = most fields wrong or missing."
    ),
    "intent_correctness": (
        "Score how correctly the intent was classified. "
        "5 = exact match with correct confidence, "
        "1 = completely wrong classification."
    ),
    "hungarian_quality": (
        "Score the quality of Hungarian language output. "
        "5 = grammatically correct, natural phrasing, proper accents, "
        "1 = broken grammar, mixed languages, missing accents."
    ),
}

# ---------------------------------------------------------------------------
# Token cost estimates per model (USD per 1K tokens, input/output avg)
# ---------------------------------------------------------------------------

_MODEL_COST_PER_1K: dict[str, float] = {
    "gpt-4o-mini": 0.00030,
    "gpt-4o": 0.00750,
    "gpt-4-turbo": 0.02000,
    "gpt-3.5-turbo": 0.00100,
    "claude-3-haiku": 0.00050,
    "claude-3-sonnet": 0.00600,
    "claude-3-opus": 0.03000,
}

# Average tokens per adapter method call (rough estimates)
_METHOD_TOKEN_ESTIMATES: dict[str, int] = {
    "classify": 500,
    "extract": 2000,
    "fetch_emails": 100,
    "send": 200,
    "filter": 100,
    "rerank": 1000,
    "chunk": 300,
    "clean": 200,
    "enrich": 800,
    "parse": 1500,
    "extract_entities": 1200,
    "ingest": 500,
    "evaluate_rubric": 800,
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class QualityService(BaseService):
    """LLM quality evaluation and cost estimation (pure compute, no DB)."""

    def __init__(self, config: QualityConfig | None = None) -> None:
        self._quality_config = config or QualityConfig()
        self._evaluations: list[RubricResult] = []
        self._cost_today: float = 0.0
        self._cost_month: float = 0.0
        super().__init__(self._quality_config)

    @property
    def service_name(self) -> str:
        return "quality"

    @property
    def service_description(self) -> str:
        return "LLM quality evaluation and cost estimation service"

    async def _start(self) -> None:
        self._logger.info(
            "quality_service_started",
            default_model=self._quality_config.default_model,
            rubric_count=len(BUILTIN_RUBRICS),
        )

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------

    async def evaluate_rubric(
        self,
        actual: str,
        rubric: str,
        expected: str | None = None,
        model: str | None = None,
    ) -> RubricResult:
        """Evaluate a response against a rubric.

        Uses the built-in rubric description if *rubric* matches a known
        name, otherwise treats it as a custom rubric string.

        For unit-testability this uses a deterministic scoring heuristic
        instead of calling a real LLM.  A production implementation would
        call ModelClient.generate() with a structured prompt.
        """
        used_model = model or self._quality_config.default_model
        rubric_text = BUILTIN_RUBRICS.get(rubric, rubric)

        # Deterministic heuristic scoring (no LLM call)
        score = self._heuristic_score(actual, expected, rubric_text)
        passed = score >= self._quality_config.pass_threshold

        reasoning = self._build_reasoning(actual, expected, rubric_text, score)

        result = RubricResult(
            score=round(score, 3),
            pass_=passed,
            reasoning=reasoning,
            rubric=rubric,
            model=used_model,
        )

        self._evaluations.append(result)
        self._logger.info(
            "rubric_evaluated",
            rubric=rubric,
            score=result.score,
            passed=passed,
            model=used_model,
        )
        return result

    async def get_overview(self) -> QualityOverview:
        """Return aggregated quality metrics."""
        total = len(self._evaluations)
        if total == 0:
            return QualityOverview()

        avg = sum(e.score for e in self._evaluations) / total
        pass_count = sum(1 for e in self._evaluations if e.pass_)
        pass_rate = pass_count / total

        return QualityOverview(
            total_evaluations=total,
            avg_score=round(avg, 3),
            pass_rate=round(pass_rate, 3),
            cost_today=self._cost_today,
            cost_month=self._cost_month,
        )

    async def estimate_pipeline_cost(
        self,
        steps: list[dict[str, Any]],
        model: str | None = None,
    ) -> CostEstimate:
        """Estimate token usage and cost for a pipeline definition."""
        used_model = model or self._quality_config.default_model
        cost_per_1k = _MODEL_COST_PER_1K.get(used_model, 0.001)

        total_tokens = 0
        for step in steps:
            method = step.get("method", "")
            tokens = _METHOD_TOKEN_ESTIMATES.get(method, 500)
            total_tokens += tokens

        estimated_cost = (total_tokens / 1000.0) * cost_per_1k

        self._logger.info(
            "cost_estimated",
            steps=len(steps),
            tokens=total_tokens,
            cost_usd=round(estimated_cost, 6),
            model=used_model,
        )

        return CostEstimate(
            estimated_tokens=total_tokens,
            estimated_cost_usd=round(estimated_cost, 6),
            model=used_model,
        )

    def list_rubrics(self) -> dict[str, str]:
        """Return all built-in rubric definitions."""
        return dict(BUILTIN_RUBRICS)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic_score(
        actual: str,
        expected: str | None,
        rubric_text: str,
    ) -> float:
        """Deterministic scoring heuristic for testing.

        If expected is provided, score based on overlap.
        Otherwise, score based on response length and structure.
        """
        if not actual or not actual.strip():
            return 0.0

        if expected and expected.strip():
            # Token overlap scoring
            actual_tokens = set(actual.lower().split())
            expected_tokens = set(expected.lower().split())
            if not expected_tokens:
                return 0.5
            overlap = len(actual_tokens & expected_tokens)
            total = len(expected_tokens)
            return min(1.0, overlap / total)

        # No expected: score based on response quality signals
        score = 0.3  # base score for non-empty response
        if len(actual) > 50:
            score += 0.2
        if len(actual) > 200:
            score += 0.1
        if "\n" in actual:
            score += 0.1
        if any(c in actual for c in ".!?"):
            score += 0.1
        return min(1.0, score)

    @staticmethod
    def _build_reasoning(
        actual: str,
        expected: str | None,
        rubric_text: str,
        score: float,
    ) -> str:
        """Build human-readable reasoning for the score."""
        parts: list[str] = []
        parts.append(f"Rubric: {rubric_text[:100]}")

        if expected:
            parts.append(f"Scored by token overlap with expected output. Score: {score:.3f}")
        else:
            parts.append(f"Scored by response quality heuristics. Score: {score:.3f}")

        if score >= 0.8:
            parts.append("Assessment: Good quality.")
        elif score >= 0.5:
            parts.append("Assessment: Acceptable quality.")
        else:
            parts.append("Assessment: Below threshold, needs improvement.")

        return " | ".join(parts)
