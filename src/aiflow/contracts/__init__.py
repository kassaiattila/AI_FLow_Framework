"""AIFlow v2 domain contracts (v1 stubs).

Full v2 contract set arrives in Phase 2b (v1.5.1). Classes under this
package are deliberately minimal — just enough to plumb results between
the source adapters, provider registry, and downstream pipeline steps.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I / §10.3
"""

from __future__ import annotations

from aiflow.contracts.extraction_result import ExtractionResult
from aiflow.contracts.parser_result import ParserResult
from aiflow.contracts.routing_decision import RoutingDecision

__all__ = [
    "ExtractionResult",
    "ParserResult",
    "RoutingDecision",
]
