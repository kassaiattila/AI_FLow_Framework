"""Cost tracking and budget management.

Tracks per-step LLM costs and enforces team-level budgets.

Usage:
    from aiflow.observability.cost_tracker import CostTracker, CostRecord
    tracker = CostTracker()
    await tracker.record(CostRecord(
        workflow_run_id="run-123",
        step_name="summarize",
        model="gpt-4o",
        provider="openai",
        input_tokens=1200,
        output_tokens=350,
        cost_usd=0.0042,
        team_id="team-abc",
    ))
    status = await tracker.check_budget("team-abc", budget_limit=100.0)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "CostRecord",
    "BudgetAlert",
    "BudgetStatus",
    "CostTracker",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BudgetAlert(str, Enum):
    """Budget alert levels."""

    NONE = "none"
    WARNING = "warning"      # >= 80 %
    CRITICAL = "critical"    # >= 95 %
    EXCEEDED = "exceeded"    # >= 100 %


class CostRecord(BaseModel):
    """Single cost entry for one workflow step invocation."""

    workflow_run_id: str
    step_name: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    team_id: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BudgetStatus(BaseModel):
    """Result of a budget check for a team."""

    team_id: str
    used_usd: float
    limit_usd: float
    remaining_usd: float
    usage_pct: float
    alert: BudgetAlert


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

class CostTracker:
    """In-memory cost tracker with budget enforcement.

    In production, this should be backed by the ``cost_records`` table
    (see migration 006) and aggregate queries. This in-memory version
    is suitable for testing and local development.
    """

    def __init__(self) -> None:
        self._records: list[CostRecord] = []
        self._by_run: dict[str, list[CostRecord]] = defaultdict(list)
        self._by_team: dict[str, list[CostRecord]] = defaultdict(list)

    # -- recording ----------------------------------------------------------

    async def record(self, cost_record: CostRecord) -> None:
        """Record a cost entry."""
        self._records.append(cost_record)
        self._by_run[cost_record.workflow_run_id].append(cost_record)
        if cost_record.team_id:
            self._by_team[cost_record.team_id].append(cost_record)
        logger.info(
            "cost_recorded",
            workflow_run_id=cost_record.workflow_run_id,
            step=cost_record.step_name,
            model=cost_record.model,
            cost_usd=cost_record.cost_usd,
            team_id=cost_record.team_id,
        )

    # -- querying -----------------------------------------------------------

    async def get_workflow_cost(self, run_id: str) -> float:
        """Return total USD cost for a single workflow run."""
        records = self._by_run.get(run_id, [])
        total = sum(r.cost_usd for r in records)
        logger.debug("workflow_cost_queried", run_id=run_id, total_usd=total, records=len(records))
        return total

    async def get_team_usage(
        self,
        team_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> float:
        """Return total USD usage for a team within an optional time window."""
        records = self._by_team.get(team_id, [])
        if period_start:
            records = [r for r in records if r.recorded_at >= period_start]
        if period_end:
            records = [r for r in records if r.recorded_at <= period_end]
        total = sum(r.cost_usd for r in records)
        logger.debug("team_usage_queried", team_id=team_id, total_usd=total, records=len(records))
        return total

    async def get_model_breakdown(self, run_id: str) -> dict[str, float]:
        """Return cost breakdown by model for a workflow run."""
        breakdown: dict[str, float] = defaultdict(float)
        for record in self._by_run.get(run_id, []):
            breakdown[record.model] += record.cost_usd
        return dict(breakdown)

    # -- budget enforcement -------------------------------------------------

    async def check_budget(self, team_id: str, budget_limit: float) -> BudgetStatus:
        """Check a team's budget status.

        Args:
            team_id: Team identifier.
            budget_limit: Monthly budget cap in USD.

        Returns:
            BudgetStatus with usage percentage and alert level.
        """
        used = await self.get_team_usage(team_id)
        remaining = max(budget_limit - used, 0.0)
        pct = (used / budget_limit * 100.0) if budget_limit > 0 else 0.0

        if pct >= 100.0:
            alert = BudgetAlert.EXCEEDED
        elif pct >= 95.0:
            alert = BudgetAlert.CRITICAL
        elif pct >= 80.0:
            alert = BudgetAlert.WARNING
        else:
            alert = BudgetAlert.NONE

        status = BudgetStatus(
            team_id=team_id,
            used_usd=round(used, 4),
            limit_usd=round(budget_limit, 4),
            remaining_usd=round(remaining, 4),
            usage_pct=round(pct, 2),
            alert=alert,
        )

        if alert != BudgetAlert.NONE:
            logger.warning(
                "budget_alert",
                team_id=team_id,
                alert=alert.value,
                used_usd=status.used_usd,
                limit_usd=status.limit_usd,
                usage_pct=status.usage_pct,
            )

        return status

    # -- introspection (test helper) ----------------------------------------

    @property
    def records(self) -> list[CostRecord]:
        """All recorded cost entries."""
        return list(self._records)
