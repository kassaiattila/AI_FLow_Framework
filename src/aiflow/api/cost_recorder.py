"""Persistent cost recording — Sprint U S154 thin shim over CostAttributionRepository.

This module previously owned its own ``cost_records`` INSERT path with an
inline DDL hack that ran on every call (``ALTER TABLE cost_records ALTER
COLUMN workflow_run_id DROP NOT NULL``). Sprint U S154 (SN-FU) consolidates
the cost-recording surface: ``record_cost`` is now a thin shim that builds a
:class:`aiflow.contracts.cost_attribution.CostAttribution` and delegates to
:class:`aiflow.state.cost_repository.CostAttributionRepository.insert_attribution`.

Behavior preserved:

* Best-effort — logs warning on failure but never raises (existing contract).
* ``workflow_run_id`` may be ``None`` (cost recorded before the workflow_run
  is persisted; the repository handles ``None`` UUIDs).

Removed:

* Inline ``ALTER TABLE`` DDL — Alembic owns schema; the previous one-time
  migration was applied long ago. Subsequent calls were running it under
  ``IF EXISTS`` guards (no-ops) but still acquiring catalog locks.

Migration sequence: existing call sites continue to use ``record_cost(...)``.
A follow-up sprint may migrate them to call the repository directly and
delete this shim. Until then ``scripts/audit_cost_recording.py --strict``
tracks remaining call sites.
"""

from __future__ import annotations

import uuid

import structlog

from aiflow.api.deps import get_pool
from aiflow.contracts.cost_attribution import CostAttribution
from aiflow.state.cost_repository import CostAttributionRepository

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

    Sprint U S154: thin shim over CostAttributionRepository. The legacy
    ``team_id`` argument is mapped to ``tenant_id`` on
    :class:`CostAttribution` (string-cast). When ``team_id`` is ``None`` the
    tenant defaults to ``"default"`` so the contract's ``min_length=1``
    constraint never trips on legacy callers that pre-date the multi-tenant
    boundary.

    Best-effort: logs warning on failure but never raises.
    """
    try:
        pool = await get_pool()
        provider = model.split("/")[0] if "/" in model else "unknown"
        tenant_id = str(team_id) if team_id else "default"

        attribution = CostAttribution(
            tenant_id=tenant_id,
            run_id=str(workflow_run_id) if workflow_run_id else None,
            skill=step_name,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

        repo = CostAttributionRepository(pool)
        await repo.insert_attribution(attribution)

        logger.info(
            "cost_recorded",
            run_id=str(workflow_run_id) if workflow_run_id else None,
            step=step_name,
            model=model,
            tokens=input_tokens + output_tokens,
            cost_usd=round(cost_usd, 6),
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.warning("cost_record_failed", error=str(e), step=step_name)
