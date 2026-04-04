"""SLA deadline checker — periodic job that escalates overdue reviews.

Can be invoked by:
1. APScheduler cron job (every 15 minutes)
2. Manual trigger via POST /api/v1/reviews/sla/check-and-escalate
3. CLI: python -m aiflow.execution.sla_checker
"""

from __future__ import annotations

import asyncio

import structlog

__all__ = ["check_sla_deadlines", "register_sla_job"]

logger = structlog.get_logger(__name__)

# Default SLA config
DEFAULT_SLA_HOURS = 24.0


async def check_sla_deadlines(sla_hours: float = DEFAULT_SLA_HOURS) -> dict:
    """Check and escalate overdue reviews. Returns summary dict."""
    from aiflow.services.human_review import HumanReviewService

    svc = HumanReviewService()
    escalated = await svc.check_and_escalate(sla_hours=sla_hours)

    summary = {
        "escalated_count": len(escalated),
        "escalated_ids": [r.id for r in escalated],
        "sla_hours": sla_hours,
    }

    if escalated:
        logger.warning("sla_check_escalated", **summary)
    else:
        logger.info("sla_check_ok", sla_hours=sla_hours)

    return summary


def register_sla_job(scheduler: object) -> None:
    """Register SLA checker as a cron job in the Scheduler.

    Runs every 15 minutes.
    """
    from aiflow.execution.scheduler import ScheduleDefinition, TriggerType

    sla_schedule = ScheduleDefinition(
        name="sla_deadline_checker",
        workflow_name="__internal__/sla_check",
        trigger_type=TriggerType.cron,
        cron_expression="*/15 * * * *",
        input_data={"sla_hours": DEFAULT_SLA_HOURS},
        priority=5,
        enabled=True,
    )

    if hasattr(scheduler, "add_schedule"):
        scheduler.add_schedule(sla_schedule)
        logger.info("sla_job_registered", cron="*/15 * * * *")


if __name__ == "__main__":
    result = asyncio.run(check_sla_deadlines())
    print(f"SLA check result: {result}")
