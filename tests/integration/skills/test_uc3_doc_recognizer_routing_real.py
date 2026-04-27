"""
@test_registry:
    suite: skills-integration
    component: services.email_connector.orchestrator (SX-2 routing layer — real)
    covers:
        - src/aiflow/services/email_connector/orchestrator.py (_route_extract_by_doctype)
        - src/aiflow/services/document_recognizer/orchestrator.py
        - skills/invoice_processor/workflows/process.py
    phase: 2
    priority: high
    estimated_duration_ms: 90000
    requires_services: [postgres, openai]
    tags: [integration, uc3, sprint-x, sx2, routing, doc-recognizer, real-llm]

Sprint X / SX-2 — composite gate (b)+(c) integration test.

Skipped by default. To run locally::

    OPENAI_API_KEY=sk-...  uv run pytest \
        tests/integration/skills/test_uc3_doc_recognizer_routing_real.py -v

Two-fixture corpus exercises both dispatch arms on the flag-on path:

* ``tests/fixtures/uc3_routing/hu_invoice_sample.eml`` — must route to
  ``invoice_processor`` and surface ``invoice_number`` in the extraction
  payload (UC1 byte-stable property).
* ``tests/fixtures/uc3_routing/hu_id_card_sample.eml`` — must route to
  ``doc_recognizer_workflow`` and surface ≥ 3 fields with
  ``confidence ≥ 0.7`` (id_card capability gate).

The fixture directory is intentionally not part of the SX-2 PR itself —
SW-1 already shipped the synthetic 8-fixture starter corpus for
DocRecognizer; the operator wires the EML wrapper for this gate during
SX-2 execution. This file provides the test scaffold so the gate stays
visible in CI as a skipped row until that corpus lands.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="SX-2 real-LLM gate requires OPENAI_API_KEY",
    ),
]


_FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "uc3_routing"


def _fixture(name: str) -> Path:
    path = _FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"SX-2 fixture not present: {path.relative_to(_FIXTURE_DIR.parent.parent)}")
    return path


async def test_hu_invoice_routes_to_invoice_processor() -> None:
    """Composite gate (b) — flag-on hu_invoice path stays UC1 byte-stable."""
    from aiflow.core.config import UC3DocRecognizerRoutingSettings, UC3ExtractionSettings
    from aiflow.services.email_connector.orchestrator import (
        _route_extract_by_doctype,
        build_default_doc_recognizer_orchestrator,
    )

    eml = _fixture("hu_invoice_sample.eml")
    # The fixture loader (operator-supplied) is expected to produce an
    # IntakeFile list — until then this remains a skipped scaffold.
    from tests.fixtures.uc3_routing.loader import load_attachments  # type: ignore[import-not-found]

    attachments = load_attachments(eml)
    payload = await _route_extract_by_doctype(
        attachments,
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True),
        extraction_settings=UC3ExtractionSettings(enabled=True, total_budget_seconds=60.0),
        tenant_id="sx2-int",
        doc_recognizer_orchestrator=build_default_doc_recognizer_orchestrator(),
    )

    assert payload is not None
    rd = payload["routing_decision"]
    assert rd["attachments"][0]["doctype_detected"] == "hu_invoice"
    assert rd["attachments"][0]["extraction_path"] == "invoice_processor"
    assert rd["attachments"][0]["extraction_outcome"] == "succeeded"
    fields = next(iter(payload["extracted_fields"].values()))
    assert (fields.get("header") or {}).get("invoice_number")


async def test_hu_id_card_routes_to_doc_recognizer() -> None:
    """Composite gate (c) — id_card extraction yields ≥ 3 fields ≥ 0.7."""
    from aiflow.core.config import UC3DocRecognizerRoutingSettings, UC3ExtractionSettings
    from aiflow.services.email_connector.orchestrator import (
        _route_extract_by_doctype,
        build_default_doc_recognizer_orchestrator,
    )

    eml = _fixture("hu_id_card_sample.eml")
    from tests.fixtures.uc3_routing.loader import load_attachments  # type: ignore[import-not-found]

    attachments = load_attachments(eml)
    payload = await _route_extract_by_doctype(
        attachments,
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True),
        extraction_settings=UC3ExtractionSettings(enabled=True, total_budget_seconds=60.0),
        tenant_id="sx2-int",
        doc_recognizer_orchestrator=build_default_doc_recognizer_orchestrator(),
    )

    assert payload is not None
    rd = payload["routing_decision"]
    assert rd["attachments"][0]["doctype_detected"] == "hu_id_card"
    assert rd["attachments"][0]["extraction_path"] == "doc_recognizer_workflow"
    fields_payload = next(iter(payload["extracted_fields"].values()))
    high_conf = [
        v
        for v in fields_payload["extracted_fields"].values()
        if (v.get("confidence") or 0.0) >= 0.7
    ]
    assert len(high_conf) >= 3
