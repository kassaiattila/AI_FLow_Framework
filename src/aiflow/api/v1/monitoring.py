"""Langfuse-backed span metrics for the Monitoring dashboard (S111)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aiflow.observability.tracing import get_langfuse_client

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


class ModelSpanMetric(BaseModel):
    """Aggregate span metrics for a single model within a time window."""

    model: str
    span_count: int
    avg_duration_ms: float
    p95_duration_ms: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0


class SpanMetricsResponse(BaseModel):
    """Monitoring.tsx span-metrics aggregate payload."""

    window_h: int
    from_ts: str
    to_ts: str
    total_spans: int
    models: list[ModelSpanMetric] = Field(default_factory=list)
    source: str = "backend"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((pct / 100.0) * (len(values) - 1)))))
    return values[k]


@router.get("/span-metrics", response_model=SpanMetricsResponse)
async def get_span_metrics(
    window_h: int = Query(24, ge=1, le=168, description="Look-back window in hours"),
) -> SpanMetricsResponse:
    """Aggregate Langfuse observations from the last ``window_h`` hours, grouped by model.

    Returns avg/p95 duration, token totals, and cost per model. Used by the
    ``Monitoring.tsx`` page to surface LLM-level health signals.
    """
    client = get_langfuse_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Langfuse not configured")

    to_ts = datetime.now(UTC)
    from_ts = to_ts - timedelta(hours=window_h)

    try:
        page = client.api.observations.get_many(
            from_start_time=from_ts,
            to_start_time=to_ts,
            type="GENERATION",
            limit=100,
        )
    except Exception as e:
        logger.warning("langfuse_observations_fetch_failed", error=str(e), window_h=window_h)
        raise HTTPException(status_code=502, detail=f"Langfuse fetch failed: {e}") from e

    observations = list(getattr(page, "data", []) or [])

    buckets: dict[str, dict[str, list[float] | int | float]] = {}

    for obs in observations:
        model = obs.model or "unknown"
        bucket = buckets.setdefault(
            model,
            {
                "durations_ms": [],
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            },
        )

        if obs.start_time and obs.end_time:
            duration_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
            bucket["durations_ms"].append(max(0.0, duration_ms))  # type: ignore[union-attr]
        elif obs.latency is not None:
            bucket["durations_ms"].append(max(0.0, obs.latency * 1000))  # type: ignore[union-attr]

        usage_details = obs.usage_details or {}
        usage = obs.usage
        bucket["input_tokens"] = int(bucket["input_tokens"]) + int(
            usage_details.get("input") or (usage.input if usage else 0) or 0
        )
        bucket["output_tokens"] = int(bucket["output_tokens"]) + int(
            usage_details.get("output") or (usage.output if usage else 0) or 0
        )
        cost = obs.calculated_total_cost
        if cost is None and obs.cost_details:
            cost = sum(v for v in obs.cost_details.values() if isinstance(v, int | float))
        bucket["cost_usd"] = float(bucket["cost_usd"]) + float(cost or 0.0)

    models: list[ModelSpanMetric] = []
    for name, data in buckets.items():
        durations: list[float] = data["durations_ms"]  # type: ignore[assignment]
        avg = sum(durations) / len(durations) if durations else 0.0
        models.append(
            ModelSpanMetric(
                model=name,
                span_count=len(durations),
                avg_duration_ms=round(avg, 1),
                p95_duration_ms=round(_percentile(durations, 95), 1),
                total_input_tokens=int(data["input_tokens"]),
                total_output_tokens=int(data["output_tokens"]),
                total_cost_usd=round(float(data["cost_usd"]), 6),
            )
        )
    models.sort(key=lambda m: m.span_count, reverse=True)

    return SpanMetricsResponse(
        window_h=window_h,
        from_ts=from_ts.isoformat(),
        to_ts=to_ts.isoformat(),
        total_spans=len(observations),
        models=models,
    )
