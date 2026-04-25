"""
@test_registry:
    suite: integration-skills
    component: skills.invoice_processor.workflows.process (Sprint T / S149)
    covers:
        - skills/invoice_processor/__init__.py
        - skills/invoice_processor/workflows/process.py
    phase: sprint-t-s149
    priority: high
    estimated_duration_ms: 90000
    requires_services: [openai, docling]
    tags: [integration, skills, invoice_processor, workflow, executor, sprint-t, s149, real-llm]

Sprint T S149 — flag-on parity smoke against the real OpenAI API on a
single Sprint Q fixture (``001_hu_simple.pdf``). Verifies the
executor-resolved ``invoice_extraction_chain`` prompts produce the same
``invoice_number`` value as the legacy single-prompt path (the field
Sprint Q observed at 100% baseline accuracy).

Skip-by-default: requires ``OPENAI_API_KEY`` (mirroring the S148 pattern
in ``test_email_intent_workflow.py``). Real LLM calls → ~$0.01 per run
(2 calls × 2 passes).
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env", override=False)

FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "invoices_sprint_q" / "001_hu_simple.pdf"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY for real-LLM workflow parity smoke",
    ),
]


async def _extract_with_flags(*, enabled: bool, skills_csv: str) -> dict:
    """Run parse_invoice → extract_invoice_data with the requested flag state.

    Sets env vars BEFORE re-importing the skill module so the
    module-level ``prompt_manager`` + ``prompt_workflow_executor`` are
    wired workflow-aware (mirroring the S148 integration harness).
    """
    os.environ["AIFLOW_PROMPT_WORKFLOWS__ENABLED"] = "true" if enabled else "false"
    os.environ["AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV"] = skills_csv

    # Drop cached modules so the new env vars take effect.
    for mod_name in list(sys.modules):
        if mod_name.startswith("skills.invoice_processor") or mod_name == "aiflow.core.config":
            sys.modules.pop(mod_name, None)

    config_mod = importlib.import_module("aiflow.core.config")
    config_mod.get_settings.cache_clear()  # type: ignore[attr-defined]

    pmod = importlib.import_module("skills.invoice_processor.workflows.process")

    parsed = await pmod.parse_invoice({"source_path": str(FIXTURE_PATH), "direction": "incoming"})
    extracted = await pmod.extract_invoice_data(parsed)
    return extracted


class TestInvoiceProcessorWorkflowParity:
    async def test_flag_on_matches_flag_off_invoice_number(self) -> None:
        """Both paths recover the same ``invoice_number`` for the
        deterministic Sprint Q fixture (Sprint Q S137 baseline = 100%
        on this field across the 10-fixture corpus)."""
        if not FIXTURE_PATH.exists():
            pytest.skip(f"Fixture missing: {FIXTURE_PATH}")

        flag_off = await _extract_with_flags(enabled=False, skills_csv="")
        flag_on = await _extract_with_flags(enabled=True, skills_csv="invoice_processor")

        off_file = flag_off["files"][0]
        on_file = flag_on["files"][0]

        off_inv = (off_file.get("header") or {}).get("invoice_number")
        on_inv = (on_file.get("header") or {}).get("invoice_number")

        assert off_inv, f"flag-off failed to extract invoice_number on {FIXTURE_PATH.name}"
        assert on_inv, f"flag-on failed to extract invoice_number on {FIXTURE_PATH.name}"
        assert off_inv == on_inv, f"invoice_number drift: off={off_inv!r} on={on_inv!r}"
