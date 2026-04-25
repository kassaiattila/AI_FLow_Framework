"""Integration test — RagMetricsHarness against a real RAGEngineService.

@test_registry
suite: integration_services_rag_metrics
component: aiflow.services.rag_metrics
covers:
  - src/aiflow/services/rag_metrics/harness.py
phase: v1.5.2
priority: medium
requires_services: [postgres]
tags: [integration, services, rag_metrics, sprint_s, s145, real]

Skip-by-default. The harness needs (1) a populated ``aszf_rag_chat`` (or
operator-overridden) collection and (2) ``OPENAI_API_KEY`` to run
``RAGEngineService.query()`` end-to-end. Operator gates the run via
``AIFLOW_RUN_NIGHTLY_RAG_METRICS=1``.

Why a real-stack test at all: the contract-shape tests live in the
unit suite. This test guards the *integration boundary* — that
``RAGEngineService.query()``'s ``QueryResult.sources[*].document_title``
keeps the shape the harness expects. If sources ever stops emitting
``document_title``, every nightly metric collapses to MRR=0 silently —
that regression is exactly what this test catches.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

pytestmark = pytest.mark.integration


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)

_COLLECTION_NAME = os.getenv("AIFLOW_NIGHTLY_RAG_COLLECTION", "aszf_rag_chat")
_QUERY_SET_PATH = _PROJECT_ROOT / "data" / "fixtures" / "rag_metrics" / "uc2_aszf_query_set.json"


def _gate_skip() -> str | None:
    if os.getenv("AIFLOW_RUN_NIGHTLY_RAG_METRICS", "") != "1":
        return "AIFLOW_RUN_NIGHTLY_RAG_METRICS=1 not set — nightly harness disabled"
    if not os.getenv("OPENAI_API_KEY"):
        return "OPENAI_API_KEY not set — RAGEngineService.query() needs an embedder"
    if not _QUERY_SET_PATH.exists():
        return f"query set fixture missing at {_QUERY_SET_PATH}"
    return None


@pytest.mark.asyncio
async def test_harness_against_real_rag_service() -> None:
    skip_reason = _gate_skip()
    if skip_reason:
        pytest.skip(skip_reason)

    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from aiflow.services.rag_engine.service import RAGEngineService
    from aiflow.services.rag_metrics import QuerySpec, RagMetricsHarness

    db_url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    rag = RAGEngineService(session_factory=session_factory)
    await rag.initialize()

    try:
        all_colls = await rag.list_collections()
        coll = next((c for c in all_colls if c.name == _COLLECTION_NAME), None)
        if coll is None:
            pytest.skip(f"collection {_COLLECTION_NAME!r} is not seeded — skip integration run")

        with _QUERY_SET_PATH.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        query_set = [QuerySpec(**spec) for spec in payload["queries"][:3]]

        harness = RagMetricsHarness(query_fn=rag.query)
        metrics = await harness.measure_collection(coll.id, query_set)
    finally:
        try:
            await rag.shutdown()
        except Exception:
            pass
        await engine.dispose()

    assert metrics.collection_id
    assert metrics.query_count == 3
    assert metrics.p95_latency_ms >= 0.0
    assert 0.0 <= metrics.mrr5 <= 1.0
    payload_line = metrics.to_jsonl()
    parsed = json.loads(payload_line)
    assert "mrr5" in parsed and "p95_latency_ms" in parsed
