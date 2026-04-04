"""SLA monitoring - track workflow latency and success rates.

Usage:
    from aiflow.observability.sla_monitor import SLAMonitor, SLADefinition
    monitor = SLAMonitor()
    monitor.register_sla(SLADefinition(
        workflow_name="process-document",
        max_duration_seconds=30,
        target_success_rate=0.99,
        alert_channels=["slack:#ops-alerts"],
    ))
    await monitor.record_run("process-document", duration_ms=1200, success=True)
    result = await monitor.check_sla("process-document")
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "SLADefinition",
    "SLAResult",
    "RunRecord",
    "SLAMonitor",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SLADefinition(BaseModel):
    """SLA contract for a workflow."""

    workflow_name: str
    max_duration_seconds: float
    target_success_rate: float = Field(ge=0.0, le=1.0, default=0.99)
    alert_channels: list[str] = Field(default_factory=list)


class RunRecord(BaseModel):
    """Single recorded workflow execution."""

    workflow_name: str
    duration_ms: float
    success: bool
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SLAResult(BaseModel):
    """Result of an SLA check against recorded runs."""

    workflow_name: str
    total_runs: int = 0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    success_rate: float = 0.0
    sla_met: bool = True
    violations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

class SLAMonitor:
    """In-memory SLA monitor that tracks latency percentiles and success rate.

    In production, this should query aggregated data from the workflow_runs
    table. This implementation stores everything in memory for testing.
    """

    def __init__(self) -> None:
        self._slas: dict[str, SLADefinition] = {}
        self._runs: dict[str, list[RunRecord]] = defaultdict(list)

    # -- configuration ------------------------------------------------------

    def register_sla(self, sla: SLADefinition) -> None:
        """Register or update an SLA definition."""
        self._slas[sla.workflow_name] = sla
        logger.info(
            "sla_registered",
            workflow=sla.workflow_name,
            max_duration_s=sla.max_duration_seconds,
            target_success=sla.target_success_rate,
        )

    def get_sla(self, workflow_name: str) -> SLADefinition | None:
        """Get the SLA definition for a workflow."""
        return self._slas.get(workflow_name)

    # -- recording ----------------------------------------------------------

    async def record_run(
        self,
        workflow_name: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record a single workflow execution."""
        record = RunRecord(
            workflow_name=workflow_name,
            duration_ms=duration_ms,
            success=success,
        )
        self._runs[workflow_name].append(record)
        logger.debug(
            "sla_run_recorded",
            workflow=workflow_name,
            duration_ms=duration_ms,
            success=success,
        )

    # -- checking -----------------------------------------------------------

    async def check_sla(self, workflow_name: str) -> SLAResult:
        """Check SLA compliance for a workflow based on recorded runs.

        Returns:
            SLAResult with percentile latencies, success rate, and violations.
        """
        runs = self._runs.get(workflow_name, [])

        if not runs:
            logger.warning("sla_check_no_data", workflow=workflow_name)
            return SLAResult(workflow_name=workflow_name, sla_met=True)

        durations = [r.duration_ms for r in runs]
        successes = sum(1 for r in runs if r.success)
        total = len(runs)
        success_rate = successes / total if total > 0 else 0.0

        # Compute percentiles
        sorted_durations = sorted(durations)
        p50 = _percentile(sorted_durations, 50)
        p95 = _percentile(sorted_durations, 95)
        p99 = _percentile(sorted_durations, 99)

        # Check SLA violations
        violations: list[str] = []
        sla = self._slas.get(workflow_name)

        if sla:
            max_ms = sla.max_duration_seconds * 1000
            if p95 > max_ms:
                violations.append(
                    f"p95 latency ({p95:.0f}ms) exceeds max ({max_ms:.0f}ms)"
                )
            if success_rate < sla.target_success_rate:
                violations.append(
                    f"success rate ({success_rate:.2%}) below target ({sla.target_success_rate:.2%})"
                )

        sla_met = len(violations) == 0

        result = SLAResult(
            workflow_name=workflow_name,
            total_runs=total,
            p50_ms=round(p50, 2),
            p95_ms=round(p95, 2),
            p99_ms=round(p99, 2),
            success_rate=round(success_rate, 4),
            sla_met=sla_met,
            violations=violations,
        )

        if not sla_met:
            logger.warning(
                "sla_violation",
                workflow=workflow_name,
                violations=violations,
                p95_ms=result.p95_ms,
                success_rate=result.success_rate,
            )
        else:
            logger.info(
                "sla_check_passed",
                workflow=workflow_name,
                p95_ms=result.p95_ms,
                success_rate=result.success_rate,
            )

        return result

    # -- introspection (test helper) ----------------------------------------

    @property
    def runs(self) -> dict[str, list[RunRecord]]:
        """All recorded runs by workflow name."""
        return dict(self._runs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute a percentile from a pre-sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (pct / 100.0) * (len(sorted_values) - 1)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[-1]
    d = k - f
    return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])
