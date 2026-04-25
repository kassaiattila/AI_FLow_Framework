#!/usr/bin/env python3
"""Nightly RAG retrieval-quality runner — Sprint S / S145 (SS-FU-3).

Usage::

    python scripts/run_nightly_rag_metrics.py \\
        --collection-id aszf_rag_chat \\
        --query-set data/fixtures/rag_metrics/uc2_aszf_query_set.json \\
        --output jsonl

Outputs one JSON line per measured collection on stdout. The line is
shaped exactly like ``CollectionMetrics.model_dump_json()``.

The script is *side-effect-free at the DB level* by default (no row is
written). Persistence is the operator's job — pipe stdout into a log
file, an OpenSearch ingest, or a future ``rag_collection_metrics``
table. Keeping persistence external preserves an air-gap-safe path.

The script is intended to run from a cron entry; see
``docs/runbooks/rag_metrics_nightly.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Source-on-path so this script runs without a system install.
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from aiflow.services.rag_metrics import (  # noqa: E402
    QuerySpec,
    RagMetricsHarness,
)

logger = structlog.get_logger(__name__)


def _load_query_set(path: Path) -> list[QuerySpec]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    raw = payload["queries"] if "queries" in payload else payload
    return [QuerySpec(**spec) for spec in raw]


async def _run(collection_id: str, query_set_path: Path, output: str) -> int:
    query_set = _load_query_set(query_set_path)

    import os

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from aiflow.services.rag_engine.service import RAGEngineService

    db_url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    rag = RAGEngineService(session_factory=session_factory)
    await rag.initialize()
    try:
        harness = RagMetricsHarness(query_fn=rag.query)
        metrics = await harness.measure_collection(collection_id, query_set)
    finally:
        try:
            await rag.shutdown()
        except Exception:
            pass
        await engine.dispose()

    if output == "jsonl":
        print(metrics.to_jsonl())
    elif output == "table":
        print(
            f"collection_id={metrics.collection_id} "
            f"mrr5={metrics.mrr5:.4f} "
            f"p95_latency_ms={metrics.p95_latency_ms:.2f} "
            f"query_count={metrics.query_count} "
            f"measured_at={metrics.measured_at.isoformat()}"
        )
    else:
        raise SystemExit(f"unknown --output mode: {output!r}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument(
        "--query-set",
        required=True,
        type=Path,
        help="Path to the QuerySpec JSON file (see data/fixtures/rag_metrics/).",
    )
    parser.add_argument(
        "--output",
        choices=["jsonl", "table"],
        default="jsonl",
    )
    args = parser.parse_args(argv)

    return asyncio.run(_run(args.collection_id, args.query_set, args.output))


if __name__ == "__main__":
    raise SystemExit(main())
