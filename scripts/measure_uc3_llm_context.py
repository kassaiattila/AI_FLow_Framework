"""Measure Sprint P / S131 LLM-context + classifier-strategy matrix.

Runs the 25-fixture corpus four times:

    (1) SKLEARN_ONLY + LLM_CONTEXT=false   ← Sprint O baseline (32%)
    (2) SKLEARN_ONLY + LLM_CONTEXT=true    ← FU-6 LLM-context-only
        (expected minimal effect because SKLEARN path skips _classify_llm)
    (3) SKLEARN_FIRST + LLM_CONTEXT=false  ← LLM-fallback, no context
    (4) SKLEARN_FIRST + LLM_CONTEXT=true   ← full Sprint P target

For each combo: misclass rate overall + per cohort, mean latency, LLM
call count (estimated), rough USD cost.

Writes ``docs/uc3_llm_context_baseline.md``. Requires:
    - Live Postgres (localhost:5433 default)
    - OPENAI_API_KEY in env (.env autoloaded)
    - ModelClient on the classifier service (AIFLOW_MODELS__* vars or
      OPENAI_API_KEY fallback — ClassifierService wires them up)

STOP conditions (HARD):
    - Wall-clock > 600 s for all 4 combos combined.
    - LLM cost per single combo > $0.20 (hard ceiling per plan §4).
    - OpenAI returns 401 or persistent 429 > 10 min.
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import yaml
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env", override=False)

from aiflow.api.deps import get_pool  # noqa: E402
from aiflow.core.config import UC3AttachmentIntentSettings  # noqa: E402
from aiflow.models.backends.litellm_backend import LiteLLMBackend  # noqa: E402
from aiflow.models.client import ModelClient  # noqa: E402

# Pin runtime imports against the PostToolUse autoformatter's unused-import stripper.
_RUNTIME_HOOKS = (LiteLLMBackend, ModelClient)
from aiflow.services.classifier.service import (  # noqa: E402
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
)
from aiflow.services.email_connector.orchestrator import (  # noqa: E402
    WORKFLOW_NAME,
    scan_and_classify,
)
from aiflow.sources import EmailSourceAdapter, IntakePackageSink  # noqa: E402
from aiflow.sources.email_adapter import ImapBackendProtocol  # noqa: E402
from aiflow.state.repositories.intake import IntakeRepository  # noqa: E402
from aiflow.state.repository import StateRepository  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "emails_sprint_o"
MANIFEST_PATH = FIXTURE_DIR / "manifest.yaml"
INTENT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "email_intent_processor" / "schemas" / "v1" / "intents.json"
)
REPORT_PATH = REPO_ROOT / "docs" / "uc3_llm_context_baseline.md"
DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)

HALT_WALL_CLOCK_SECONDS = 600.0
HALT_COST_USD_PER_COMBO = 0.20


class _FakeImapBackend(ImapBackendProtocol):
    def __init__(self, raw: bytes, uid: int = 1) -> None:
        self._inbox = [(uid, raw)]
        self._seen: set[int] = set()
        self._flagged: dict[int, str] = {}

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return [(u, r) for u, r in self._inbox if u not in self._seen]

    async def mark_seen(self, uid: int) -> None:
        self._seen.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        self._flagged[uid] = reason

    async def ping(self) -> bool:
        return True


def _load_schema_labels() -> list[dict[str, Any]]:
    data = json.loads(INTENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for intent in data["intents"]:
        kw = list(intent.get("keywords_hu", [])) + list(intent.get("keywords_en", []))
        out.append(
            {
                "id": intent["id"],
                "display_name": intent.get("display_name", intent["id"]),
                "description": intent.get("description", ""),
                "keywords": kw,
                "examples": intent.get("examples", []),
            }
        )
    return out


async def _cleanup_workflow_runs(engine, tenant_id: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            sa_text(
                """DELETE FROM cost_records
                   WHERE workflow_run_id IN (
                     SELECT id FROM workflow_runs
                     WHERE workflow_name = :wf
                       AND (output_data->>'tenant_id') = :tid
                   )"""
            ),
            {"wf": WORKFLOW_NAME, "tid": tenant_id},
        )
        await conn.execute(
            sa_text(
                """DELETE FROM step_runs
                   WHERE workflow_run_id IN (
                     SELECT id FROM workflow_runs
                     WHERE workflow_name = :wf
                       AND (output_data->>'tenant_id') = :tid
                   )"""
            ),
            {"wf": WORKFLOW_NAME, "tid": tenant_id},
        )
        await conn.execute(
            sa_text(
                """DELETE FROM workflow_runs
                   WHERE workflow_name = :wf
                     AND (output_data->>'tenant_id') = :tid"""
            ),
            {"wf": WORKFLOW_NAME, "tid": tenant_id},
        )


async def _cleanup_tenant(pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1", tenant_id
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                """DELETE FROM package_associations
                   WHERE file_id IN (
                     SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[])
                   )""",
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])", ids
            )
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )


async def _run_combo(
    *,
    label: str,
    strategy: ClassificationStrategy,
    llm_context: bool,
    fixtures: list[dict[str, Any]],
    schema_labels: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run one (strategy × llm_context) combination over all 25 fixtures."""
    tenant_id = f"uc3-p-s131-{label}-{uuid4().hex[:6]}"

    pool = await get_pool()
    intake_repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=intake_repo)

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_repo = StateRepository(session_factory)

    # Wire a real LLM client (OpenAI via OPENAI_API_KEY) for the non-
    # SKLEARN_ONLY strategies. SKLEARN_ONLY doesn't touch the client so
    # we can skip the init cost there — but a valid client is harmless.
    if strategy != ClassificationStrategy.SKLEARN_ONLY:
        backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
        models_client = ModelClient(generation_backend=backend)
    else:
        models_client = None
    classifier = ClassifierService(
        config=ClassifierConfig(strategy=strategy, confidence_threshold=0.6),
        models_client=models_client,
    )
    await classifier.start()

    settings = UC3AttachmentIntentSettings(
        enabled=True, llm_context=llm_context, total_budget_seconds=60.0
    )

    per_email: list[dict[str, Any]] = []
    llm_calls = 0
    wall_start = time.perf_counter()

    try:
        with TemporaryDirectory(prefix=f"uc3_p_{label}_") as tmp:
            storage_root = Path(tmp)
            for idx, entry in enumerate(fixtures, 1):
                eml = (FIXTURE_DIR / f"{entry['id']}.eml").read_bytes()
                backend = _FakeImapBackend(eml, uid=idx)
                adapter = EmailSourceAdapter(
                    backend=backend,
                    storage_root=storage_root / entry["id"],
                    tenant_id=tenant_id,
                )
                t0 = time.perf_counter()
                try:
                    results = await scan_and_classify(
                        adapter,
                        sink,
                        classifier,
                        state_repo,
                        tenant_id=tenant_id,
                        max_items=1,
                        schema_labels=schema_labels,
                        attachment_intent_settings=settings,
                    )
                except Exception as exc:
                    per_email.append(
                        {
                            "id": entry["id"],
                            "cohort": entry["cohort"],
                            "expected_intent": entry["expected_intent"],
                            "predicted_intent": "error",
                            "method": f"error:{type(exc).__name__}",
                            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                            "correct": False,
                        }
                    )
                    continue
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                got_label = results[0][1].label if results else "unknown"
                got_method = results[0][1].method if results else "no_result"
                if "llm" in got_method or "hybrid" in got_method:
                    llm_calls += 1
                per_email.append(
                    {
                        "id": entry["id"],
                        "cohort": entry["cohort"],
                        "expected_intent": entry["expected_intent"],
                        "predicted_intent": got_label,
                        "method": got_method,
                        "latency_ms": round(elapsed_ms, 2),
                        "correct": got_label == entry["expected_intent"],
                    }
                )
    finally:
        wall_ms = (time.perf_counter() - wall_start) * 1000.0
        await classifier.stop()
        await _cleanup_workflow_runs(engine, tenant_id)
        await _cleanup_tenant(pool, tenant_id)
        await engine.dispose()

    return _aggregate(label, per_email, wall_ms, llm_calls)


def _aggregate(
    label: str, per_email: list[dict[str, Any]], wall_ms: float, llm_calls: int
) -> dict[str, Any]:
    n = len(per_email)
    correct = sum(1 for r in per_email if r["correct"])
    misclass_pct = ((n - correct) / n * 100.0) if n else 0.0

    latencies = [r["latency_ms"] for r in per_email]
    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else (max(latencies) if latencies else 0.0)
    )

    by_cohort: dict[str, dict[str, int]] = {}
    for r in per_email:
        row = by_cohort.setdefault(r["cohort"], {"total": 0, "correct": 0})
        row["total"] += 1
        if r["correct"]:
            row["correct"] += 1

    # Rough cost estimate: gpt-4o-mini ~$0.15 per 1M input tokens. Each
    # classification is ~1k tokens in + ~200 out ≈ 1200 tokens.
    approx_cost_usd = round(llm_calls * 1200 * 0.15e-6, 4)

    return {
        "label": label,
        "n": n,
        "correct": correct,
        "misclass_pct": round(misclass_pct, 2),
        "by_cohort": by_cohort,
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "wall_clock_ms": round(wall_ms, 2),
        "llm_calls": llm_calls,
        "approx_cost_usd": approx_cost_usd,
        "per_email": per_email,
    }


def _render_report(combos: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# UC3 Sprint P — LLM-context + classifier-strategy matrix")
    lines.append("")
    lines.append(
        "> Generated by `scripts/measure_uc3_llm_context.py`. "
        "Sprint O FU-7 baseline: 32% misclass (`SKLEARN_ONLY + LLM_CONTEXT=false`)."
    )
    lines.append("")

    lines.append("## Matrix")
    lines.append("")
    lines.append(
        "| # | Strategy | LLM-context | Misclass % | Invoice | Contract | Body-only | Mixed | LLM calls | Cost (USD) | p50 / p95 ms |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(combos, 1):
        inv = c["by_cohort"].get("invoice_attachment", {})
        con = c["by_cohort"].get("contract_docx", {})
        bdy = c["by_cohort"].get("body_only", {})
        mix = c["by_cohort"].get("mixed", {})

        def _frac(d: dict[str, int]) -> str:
            return f"{d.get('correct', 0)}/{d.get('total', 0)}"

        lines.append(
            f"| {i} | {c['label']} | {c['llm_context']} | **{c['misclass_pct']}%** "
            f"| {_frac(inv)} | {_frac(con)} | {_frac(bdy)} | {_frac(mix)} "
            f"| {c['llm_calls']} | ${c['approx_cost_usd']} "
            f"| {c['latency_p50_ms']:.0f} / {c['latency_p95_ms']:.0f} |"
        )
    lines.append("")

    for c in combos:
        lines.append(f"## {c['label']}")
        lines.append("")
        lines.append("| Fixture | Cohort | Expected | Predicted | OK | Method |")
        lines.append("|---|---|---|---|---|---|")
        for r in c["per_email"]:
            ok = "✅" if r["correct"] else "❌"
            lines.append(
                f"| `{r['id']}` | {r['cohort']} | `{r['expected_intent']}` | "
                f"`{r['predicted_intent']}` | {ok} | {r['method']} |"
            )
        lines.append("")
    return "\n".join(lines)


async def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "[error] OPENAI_API_KEY is not set. The LLM_FIRST + LLM_CONTEXT combos need it.",
            file=sys.stderr,
        )
        return 2

    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    fixtures = manifest["fixtures"]
    schema_labels = _load_schema_labels()

    matrix = [
        ("sklearn_only_no_ctx", ClassificationStrategy.SKLEARN_ONLY, False),
        ("sklearn_only_with_ctx", ClassificationStrategy.SKLEARN_ONLY, True),
        ("sklearn_first_no_ctx", ClassificationStrategy.SKLEARN_FIRST, False),
        ("sklearn_first_with_ctx", ClassificationStrategy.SKLEARN_FIRST, True),
    ]

    combos: list[dict[str, Any]] = []
    wall0 = time.perf_counter()
    for label, strategy, llm_ctx in matrix:
        print(f"[run] {label} (strategy={strategy.value}, llm_context={llm_ctx}) ...")
        result = await _run_combo(
            label=label,
            strategy=strategy,
            llm_context=llm_ctx,
            fixtures=fixtures,
            schema_labels=schema_labels,
        )
        result["llm_context"] = llm_ctx
        combos.append(result)
        print(
            f"  misclass={result['misclass_pct']}% llm_calls={result['llm_calls']} "
            f"cost=${result['approx_cost_usd']} wall={result['wall_clock_ms']:.0f}ms"
        )
        if result["approx_cost_usd"] > HALT_COST_USD_PER_COMBO:
            print(
                f"[HALT] combo {label} cost ${result['approx_cost_usd']} "
                f"exceeds ${HALT_COST_USD_PER_COMBO}",
                file=sys.stderr,
            )
            return 2

    total_wall_ms = (time.perf_counter() - wall0) * 1000.0

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_report(combos), encoding="utf-8")
    print(f"[ok] wrote {REPORT_PATH.relative_to(REPO_ROOT)}")

    total_cost = sum(c["approx_cost_usd"] for c in combos)
    print(f"[stats] total_wall={total_wall_ms:.0f}ms total_cost=${total_cost:.4f}")

    if total_wall_ms > HALT_WALL_CLOCK_SECONDS * 1000.0:
        print(
            f"[HALT] total wall {total_wall_ms:.0f}ms exceeds {HALT_WALL_CLOCK_SECONDS:.0f}s",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
