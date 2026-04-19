"""Routing layer — decides which ParserProvider handles each file.

Thin module introduced by S95 (Sprint I / UC1 session 2). The router
consumes size + MIME + policy signals and emits a RoutingDecision; scan-
aware signals, classifier feedback, and cost-cap constraints arrive in
later sessions.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N7 (MultiSignalRouter),
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I.
"""

from __future__ import annotations

from aiflow.routing.router import MultiSignalRouter

__all__ = [
    "MultiSignalRouter",
]
