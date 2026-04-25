"""
@test_registry:
    suite: integration-skills
    component: skills.email_intent_processor.workflows.classify (Sprint T / S148)
    covers:
        - skills/email_intent_processor/workflows/classify.py
        - skills/email_intent_processor/classifiers/__init__.py
        - skills/email_intent_processor/classifiers/llm_classifier.py
    phase: sprint-t-s148
    priority: high
    estimated_duration_ms: 30000
    requires_services: [openai]
    tags: [integration, skills, email_intent_processor, workflow, executor, sprint-t, s148, real-llm]

Sprint T S148 — flag-on parity smoke against the real OpenAI API on a
single Sprint O fixture (``001_invoice_march.eml``). Verifies the
executor-resolved ``email_intent_chain`` prompt produces the same
EXTRACT-class label as the legacy single-prompt path.

Skip-by-default: requires ``OPENAI_API_KEY`` (mirroring the Profile B
conditional-skip pattern). Real LLM call → ~$0.0002 per run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "emails_sprint_o" / "001_invoice_march.eml"
INTENT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "email_intent_processor" / "schemas" / "v1" / "intents.json"
)

EXTRACT_INTENT_IDS = {"invoice_received", "order"}

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY for real-LLM integration parity smoke",
    ),
]


def _load_intents() -> list[dict]:
    return json.loads(INTENT_SCHEMA_PATH.read_text(encoding="utf-8"))["intents"]


async def _classify_with_flags(*, enabled: bool, skills_csv: str) -> dict:
    """Run the skill's classify_intent step with the requested flag state.

    Sets env vars BEFORE importing the skill module so the module-level
    ``prompt_manager`` + ``prompt_workflow_executor`` are wired
    workflow-aware. Each call rewrites the env + reloads the skill in
    fresh sub-modules to avoid singleton caching across the two passes.
    """
    import importlib
    import sys

    os.environ["AIFLOW_PROMPT_WORKFLOWS__ENABLED"] = "true" if enabled else "false"
    os.environ["AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV"] = skills_csv

    # Drop cached modules so the new env vars take effect.
    for mod_name in list(sys.modules):
        if mod_name.startswith("skills.email_intent_processor") or mod_name == "aiflow.core.config":
            sys.modules.pop(mod_name, None)

    # Re-import after env mutation.
    config_mod = importlib.import_module("aiflow.core.config")
    config_mod.get_settings.cache_clear()  # type: ignore[attr-defined]

    cmod = importlib.import_module("skills.email_intent_processor.workflows.classify")

    raw = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")

    # The full 7-step pipeline does its own parse + attachment processing
    # via tools, but here we only need the LLM classifier's verdict on the
    # body — bypass attachment processing for a deterministic + cheap run.
    body_marker = "\n\n"
    body = raw.split(body_marker, 1)[1] if body_marker in raw else raw
    subject_line = next(
        (ln[len("Subject: ") :] for ln in raw.splitlines() if ln.startswith("Subject: ")),
        "",
    )

    return await cmod.classify_intent(
        {
            "subject": subject_line,
            "body": body,
            "attachment_text": "",
        }
    )


class TestEmailIntentWorkflowParity:
    async def test_flag_on_matches_flag_off_on_extract_fixture(self) -> None:
        """Flag-on workflow path classifies the invoice fixture into the
        same EXTRACT-class bucket as the legacy single-prompt path."""
        if not FIXTURE_PATH.exists():
            pytest.skip(f"Fixture missing: {FIXTURE_PATH}")

        flag_off = await _classify_with_flags(enabled=False, skills_csv="")
        flag_on = await _classify_with_flags(enabled=True, skills_csv="email_intent_processor")

        intents = _load_intents()
        intent_ids = {i["id"] for i in intents}

        off_id = flag_off["intent"]["intent_id"]
        on_id = flag_on["intent"]["intent_id"]

        # Both must be valid schema intents.
        assert off_id in intent_ids, f"flag-off produced unknown intent {off_id!r}"
        assert on_id in intent_ids, f"flag-on produced unknown intent {on_id!r}"

        # Either bucket-equivalence (both EXTRACT-class) or strict equality.
        if off_id in EXTRACT_INTENT_IDS or on_id in EXTRACT_INTENT_IDS:
            assert off_id in EXTRACT_INTENT_IDS and on_id in EXTRACT_INTENT_IDS, (
                f"label class drift: off={off_id!r} on={on_id!r}"
            )
        else:
            assert off_id == on_id, f"label drift on non-EXTRACT class: off={off_id!r} on={on_id!r}"
