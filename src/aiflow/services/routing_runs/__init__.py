"""Sprint X / SX-3 — routing_runs audit service.

Persistence + read-side helpers for the ``routing_runs`` table (Alembic
050). Sibling to :mod:`aiflow.services.document_recognizer.repository`
but scoped to the email-level dispatch trail emitted by
:mod:`aiflow.services.email_connector.orchestrator`.
"""

from __future__ import annotations

from aiflow.services.routing_runs.repository import (
    METADATA_BYTE_CAP,
    RoutingRunRepository,
)
from aiflow.services.routing_runs.schemas import (
    RoutingRunCreate,
    RoutingRunDetail,
    RoutingRunFilters,
    RoutingRunSummary,
    RoutingStatsBucket,
    RoutingStatsResponse,
    aggregate_outcome,
    summarize_routing_decision,
)

__all__ = [
    "METADATA_BYTE_CAP",
    "RoutingRunCreate",
    "RoutingRunDetail",
    "RoutingRunFilters",
    "RoutingRunRepository",
    "RoutingRunSummary",
    "RoutingStatsBucket",
    "RoutingStatsResponse",
    "aggregate_outcome",
    "summarize_routing_decision",
]
