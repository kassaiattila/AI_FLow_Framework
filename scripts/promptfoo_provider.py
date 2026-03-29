#!/usr/bin/env python3
"""Promptfoo custom provider for AIFlow skills.

Bridge between Promptfoo evaluation framework and AIFlow RAG/skill pipelines.
Promptfoo calls this script with a prompt, and it returns the AIFlow response.

Usage in promptfooconfig.yaml:
    providers:
      - id: "exec:python scripts/promptfoo_provider.py"
        config:
          skill: aszf-rag
          collection: azhu-test-v2
          role: expert

Promptfoo sends JSON on stdin:
    {"prompt": "user question", "config": {"skill": "...", "collection": "...", "role": "..."}}

Script returns JSON on stdout:
    {"output": "AI response text"}

Reference: Cubix RAG Module 06 (eszkozok_es_cicd.md)
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def run_rag_query(question: str, collection: str, role: str) -> str:
    """Run the RAG query pipeline and return the answer."""
    from skills.aszf_rag_chat.workflows.query import (
        rewrite_query, search_documents, build_context,
        generate_answer, extract_citations, detect_hallucination,
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
        classify_intent, elaborate, extract, review, generate_diagram,
    )

    data = {"user_input": question}
    r1 = await classify_intent(data)
    if r1.get("category") != "process":
        return f"Not a process description (category: {r1.get('category')})"

    r2 = await elaborate({**r1, "user_input": question})
    r3 = await extract(r2)
    r5 = await generate_diagram(r3)
    return f"**{r5.get('title')}**\n\n```mermaid\n{r5.get('mermaid_code', '')}\n```"


def main() -> None:
    """Promptfoo entry point - reads stdin JSON, returns stdout JSON."""
    raw = sys.stdin.read()
    request = json.loads(raw)

    prompt = request.get("prompt", "")
    config = request.get("config", {})
    skill = config.get("skill", "aszf-rag")
    collection = config.get("collection", "azhu-test-v2")
    role = config.get("role", "expert")

    if skill in ("aszf-rag", "aszf_rag_chat"):
        answer = asyncio.run(run_rag_query(prompt, collection, role))
    elif skill in ("process-doc", "process_documentation"):
        answer = asyncio.run(run_process_doc(prompt))
    else:
        answer = f"Unknown skill: {skill}"

    print(json.dumps({"output": answer}, ensure_ascii=False))


if __name__ == "__main__":
    main()
