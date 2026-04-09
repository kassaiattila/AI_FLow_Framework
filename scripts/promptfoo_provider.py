#!/usr/bin/env python3
"""Promptfoo custom provider for AIFlow skills.

Bridge between Promptfoo evaluation framework and AIFlow RAG/skill pipelines.
Promptfoo calls this script with the rendered prompt on argv (plus context
metadata as later args). This provider returns a JSON object on stdout.

Usage in promptfooconfig.yaml:
    providers:
      - id: "exec:python ../../../scripts/promptfoo_provider.py"
        label: "AIFlow RAG Expert"
        config:
          skill: aszf-rag
          collection: azhu-test-v2
          role: expert

Promptfoo invocation (exec provider, per promptfoo docs):
    python scripts/promptfoo_provider.py "<prompt>" <provider_opts_json> <context_json>

This script supports BOTH invocation styles:
    1. argv style (promptfoo exec): argv[1]=prompt, argv[2]=opts_json, argv[3]=ctx_json
    2. stdin JSON: {"prompt": "...", "config": {...}} — for manual testing / older
       promptfoo versions.

Script returns JSON on stdout:
    {"output": "AI response text"}

Windows note: stdout is force-reconfigured to UTF-8 so Hungarian characters
round-trip correctly (default Windows code page is cp1252 which mangles JSON).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path and .env is loaded.
# Using __file__ makes the script location-independent — no matter where
# promptfoo invokes us from, we can locate the AIFlow source tree.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402  (after sys.path munging)

load_dotenv(PROJECT_ROOT / ".env")

# Force UTF-8 on stdout — Windows default code page (cp1252) corrupts
# Hungarian characters when promptfoo parses our JSON response.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, OSError):
    # Python < 3.7 or stream that doesn't support reconfigure
    pass

# CRITICAL: Silence all AIFlow structlog output. promptfoo parses stdout as
# JSON, so ANY log line on stdout before our final JSON pollutes the result.
# We reroute everything to stderr + raise the level to WARNING so only real
# errors surface. This MUST happen BEFORE importing any aiflow module.
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,
)
for noisy in ("aiflow", "httpx", "httpcore", "litellm", "asyncio", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# Tell AIFlow to use minimal logging too
os.environ.setdefault("AIFLOW_LOG_LEVEL", "WARNING")
os.environ.setdefault("LITELLM_LOG", "ERROR")

try:
    import structlog

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
except ImportError:
    pass


async def run_rag_query(question: str, collection: str, role: str) -> str:
    """Run the RAG query pipeline and return the answer."""
    from skills.aszf_rag_chat.workflows.query import (
        build_context,
        detect_hallucination,
        extract_citations,
        generate_answer,
        rewrite_query,
        search_documents,
    )

    data = {
        "question": question,
        "collection": collection,
        "role": role,
        "language": "hu",
        "top_k": 5,
    }

    r1 = await rewrite_query(data)
    r2 = await search_documents({**data, **r1})
    r3 = await build_context({**data, **r2})
    r4 = await generate_answer({**data, **r3})
    r5 = await extract_citations(r4)
    r6 = await detect_hallucination(r5)

    return r6.get("answer", "")


async def run_process_doc(question: str) -> str:
    """Run the Process Documentation pipeline."""
    from skills.process_documentation.workflow import (
        classify_intent,
        elaborate,
        extract,
        generate_diagram,
    )

    data = {"user_input": question}
    r1 = await classify_intent(data)
    if r1.get("category") != "process":
        return f"Not a process description (category: {r1.get('category')})"

    r2 = await elaborate({**r1, "user_input": question})
    r3 = await extract(r2)
    r5 = await generate_diagram(r3)
    return f"**{r5.get('title')}**\n\n```mermaid\n{r5.get('mermaid_code', '')}\n```"


def _parse_request() -> tuple[str, dict]:
    """Return (prompt_text, provider_config).

    Supports promptfoo exec-provider argv style OR JSON on stdin (manual use).
    """
    # argv style: python script.py "<prompt>" <opts_json> <ctx_json>
    if len(sys.argv) >= 2:
        prompt_text = sys.argv[1]
        provider_opts: dict = {}
        if len(sys.argv) >= 3:
            try:
                raw_opts = json.loads(sys.argv[2])
                if isinstance(raw_opts, dict):
                    provider_opts = raw_opts.get("config", raw_opts)
            except (json.JSONDecodeError, TypeError):
                provider_opts = {}
        return prompt_text, provider_opts

    # stdin style (legacy / manual test)
    raw = sys.stdin.read()
    if not raw.strip():
        return "", {}
    try:
        request = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip(), {}
    return request.get("prompt", ""), request.get("config", {})


def main() -> None:
    """Promptfoo entry point — write one JSON object to stdout.

    Output contract (promptfoo exec provider):
        {"output": "<response text>"} on success
        {"error": "<error message>"} on failure
    """
    try:
        prompt, provider_config = _parse_request()
        skill = provider_config.get("skill", "aszf-rag")
        collection = provider_config.get("collection", "azhu-test-v2")
        role = provider_config.get("role", "expert")

        if not prompt.strip():
            print(json.dumps({"error": "Empty prompt"}, ensure_ascii=False))
            return

        if skill in ("aszf-rag", "aszf_rag_chat"):
            answer = asyncio.run(run_rag_query(prompt, collection, role))
        elif skill in ("process-doc", "process_documentation"):
            answer = asyncio.run(run_process_doc(prompt))
        else:
            answer = f"Unknown skill: {skill}"

        print(json.dumps({"output": answer}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001  — promptfoo expects JSON either way
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
