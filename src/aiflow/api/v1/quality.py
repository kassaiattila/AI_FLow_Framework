"""Quality API — LLM evaluation, cost estimation, rubric listing."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class EvaluateRequest(BaseModel):
    actual: str = Field(..., description="Actual LLM output to evaluate")
    rubric: str = Field(..., description="Rubric name or custom rubric text")
    expected: str | None = Field(None, description="Expected output for comparison")
    model: str | None = Field(None, description="Model to use for evaluation")


class RubricEvalResponse(BaseModel):
    score: float
    pass_: bool = Field(..., alias="pass")
    reasoning: str
    source: str = "backend"

    model_config = {"populate_by_name": True}


class QualityOverviewResponse(BaseModel):
    total_evaluations: int = 0
    avg_score: float = 0.0
    pass_rate: float = 0.0
    cost_today: float = 0.0
    cost_month: float = 0.0
    source: str = "backend"


class CostEstimateRequest(BaseModel):
    steps: list[dict[str, Any]] = Field(..., description="Pipeline steps [{service, method}, ...]")
    model: str | None = Field(None, description="Model to estimate cost for")


class CostEstimateResponse(BaseModel):
    estimated_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model: str = ""
    source: str = "backend"


class RubricsResponse(BaseModel):
    rubrics: dict[str, str]
    source: str = "backend"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=QualityOverviewResponse)
async def get_quality_overview() -> QualityOverviewResponse:
    """Get aggregated quality metrics overview."""
    from aiflow.services.quality.service import QualityConfig, QualityService

    svc = QualityService(config=QualityConfig())
    await svc.start()
    overview = await svc.get_overview()

    return QualityOverviewResponse(
        total_evaluations=overview.total_evaluations,
        avg_score=overview.avg_score,
        pass_rate=overview.pass_rate,
        cost_today=overview.cost_today,
        cost_month=overview.cost_month,
    )


@router.post("/evaluate", response_model=RubricEvalResponse)
async def evaluate_rubric(req: EvaluateRequest) -> RubricEvalResponse:
    """Evaluate an LLM output against a rubric."""
    from aiflow.services.quality.service import QualityConfig, QualityService

    svc = QualityService(config=QualityConfig())
    await svc.start()

    result = await svc.evaluate_rubric(
        actual=req.actual,
        rubric=req.rubric,
        expected=req.expected,
        model=req.model,
    )

    return RubricEvalResponse(
        score=result.score,
        **{"pass": result.pass_},
        reasoning=result.reasoning,
    )


@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_pipeline_cost(
    req: CostEstimateRequest,
) -> CostEstimateResponse:
    """Estimate token usage and cost for a pipeline."""
    from aiflow.services.quality.service import QualityConfig, QualityService

    svc = QualityService(config=QualityConfig())
    await svc.start()

    estimate = await svc.estimate_pipeline_cost(
        steps=req.steps,
        model=req.model,
    )

    return CostEstimateResponse(
        estimated_tokens=estimate.estimated_tokens,
        estimated_cost_usd=estimate.estimated_cost_usd,
        model=estimate.model,
    )


@router.get("/rubrics", response_model=RubricsResponse)
async def list_rubrics() -> RubricsResponse:
    """List all built-in quality rubrics."""
    from aiflow.services.quality.service import QualityConfig, QualityService

    svc = QualityService(config=QualityConfig())
    rubrics = svc.list_rubrics()
    return RubricsResponse(rubrics=rubrics)
