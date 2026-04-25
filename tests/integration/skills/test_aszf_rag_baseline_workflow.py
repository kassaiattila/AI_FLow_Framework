"""
@test_registry:
    suite: integration-skills
    component: skills.aszf_rag_chat.workflows.query (Sprint T / S150)
    covers:
        - skills/aszf_rag_chat/__init__.py
        - skills/aszf_rag_chat/workflows/query.py
    phase: sprint-t-s150
    priority: high
    estimated_duration_ms: 60000
    requires_services: [openai]
    tags: [integration, skills, aszf_rag_chat, workflow, executor, sprint-t, s150, real-llm]

Sprint T S150 — flag-on vs flag-off parity smoke against the real
OpenAI API on a single deterministic baseline-persona query drawn from
the Sprint S S145 nightly UC2 corpus
(``data/fixtures/rag_metrics/uc2_aszf_query_set.json``).

The descriptor (`prompts/workflows/aszf_rag_chain.yaml`) resolves the
same nested prompt YAMLs (`aszf-rag/query_rewriter`, ...) the legacy
path uses, so the workflow-resolved ``rewrite_query`` step must produce
a byte-stable rewritten query for the baseline persona.

Skip-by-default: requires ``OPENAI_API_KEY``. Real LLM calls →
~$0.002 per run (2 calls × 1 query).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env", override=False)

QUERY_SET_PATH = REPO_ROOT / "data" / "fixtures" / "rag_metrics" / "uc2_aszf_query_set.json"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY for real-LLM workflow parity smoke",
    ),
]


def _load_first_question() -> str:
    if not QUERY_SET_PATH.exists():
        pytest.skip(f"UC2 query set missing: {QUERY_SET_PATH}")
    with open(QUERY_SET_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    queries = payload.get("queries") or []
    if not queries:
        pytest.skip("UC2 query set has no queries")
    return queries[0]["question"]


async def _rewrite_with_flags(*, enabled: bool, skills_csv: str, question: str) -> str:
    """Run rewrite_query under the requested flag state and return the
    rewritten query string.

    Sets env vars BEFORE re-importing the skill module so the
    module-level ``_prompt_manager`` + ``prompt_workflow_executor`` are
    wired workflow-aware (mirrors the S149 integration harness).
    """
    os.environ["AIFLOW_PROMPT_WORKFLOWS__ENABLED"] = "true" if enabled else "false"
    os.environ["AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV"] = skills_csv

    for mod_name in list(sys.modules):
        if mod_name.startswith("skills.aszf_rag_chat") or mod_name == "aiflow.core.config":
            sys.modules.pop(mod_name, None)

    config_mod = importlib.import_module("aiflow.core.config")
    config_mod.get_settings.cache_clear()  # type: ignore[attr-defined]

    qmod = importlib.import_module("skills.aszf_rag_chat.workflows.query")
    out = await qmod.rewrite_query({"question": question, "role": "baseline"})
    return out["rewritten_query"]


class TestAszfRagBaselineWorkflowParity:
    async def test_flag_on_baseline_rewrite_runs_through_workflow(self) -> None:
        """Flag-on baseline path must execute the workflow-resolved
        rewrite_query without raising and return a non-empty rewritten
        query. Sprint J UC2 retrieval-quality contract is preserved
        because the descriptor resolves the same ``aszf-rag/query_rewriter``
        YAML the legacy path uses."""
        question = _load_first_question()

        flag_off = await _rewrite_with_flags(enabled=False, skills_csv="", question=question)
        flag_on = await _rewrite_with_flags(
            enabled=True, skills_csv="aszf_rag_chat", question=question
        )

        assert flag_off, "flag-off rewrite returned empty"
        assert flag_on, "flag-on rewrite returned empty"
        # Same descriptor + legacy YAML → same prompt → high lexical overlap.
        # We don't assert byte-equality (LLM nondeterminism on temperature>0)
        # but the rewritten queries must overlap on most tokens for the
        # retrieval surface to remain usable.
        off_tokens = set(flag_off.lower().split())
        on_tokens = set(flag_on.lower().split())
        if not off_tokens or not on_tokens:
            pytest.fail(f"empty token set: off={flag_off!r} on={flag_on!r}")
        jaccard = len(off_tokens & on_tokens) / len(off_tokens | on_tokens)
        assert jaccard >= 0.5, (
            f"rewritten-query token overlap too low (jaccard={jaccard:.2f}): "
            f"off={flag_off!r} on={flag_on!r}"
        )
