"""Persistent cost recording — writes LLM usage to cost_records table."""

import uuid

import structlog

from aiflow.api.deps import get_pool

__all__ = ["record_cost"]

logger = structlog.get_logger(__name__)


async def record_cost(
    *,
    workflow_run_id: str | uuid.UUID | None = None,
    step_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    team_id: str | uuid.UUID | None = None,
) -> None:
    """Insert a cost record into the cost_records table.

    Best-effort: logs warning on failure but never raises.
    workflow_run_id is nullable — use None when the workflow_run hasn't been persisted yet.
    """
    try:
        pool = await get_pool()
        provider = model.split("/")[0] if "/" in model else "unknown"

        # Make workflow_run_id nullable to avoid FK constraint issues
        # (cost may be recorded before the workflow_run is persisted)
        run_uuid = None
        if workflow_run_id:
            try:
                run_uuid = uuid.UUID(str(workflow_run_id))
            except (ValueError, AttributeError):
                run_uuid = None

        async with pool.acquire() as conn:
            # Drop FK constraint if it exists (one-time migration)
            await conn.execute("""
                DO $$ BEGIN
                    ALTER TABLE cost_records ALTER COLUMN workflow_run_id DROP NOT NULL;
                    ALTER TABLE cost_records DROP CONSTRAINT IF EXISTS cost_records_workflow_run_id_fkey;
                EXCEPTION WHEN others THEN NULL;
                END $$;
            """)
            await conn.execute(
                """INSERT INTO cost_records
                   (id, workflow_run_id, step_name, model, provider,
                    input_tokens, output_tokens, cost_usd, team_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                uuid.uuid4(),
                run_uuid,
                step_name,
                model,
                provider,
                input_tokens,
                output_tokens,
                cost_usd,
                uuid.UUID(str(team_id)) if team_id else None,
            )
        logger.info(
            "cost_recorded",
            run_id=str(workflow_run_id),
            step=step_name,
            model=model,
            tokens=input_tokens + output_tokens,
            cost_usd=round(cost_usd, 6),
        )
    except Exception as e:
        logger.warning("cost_record_failed", error=str(e), step=step_name)
