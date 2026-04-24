"""Measure Sprint O / S128 attachment-intent flag-ON misclass rate.

Sister script of ``scripts/measure_uc3_baseline.py`` — runs the same 25
fixture corpus through the orchestrator with
``UC3AttachmentIntentSettings(enabled=True)`` and the rule boost active.
Compares per-cohort against the S126 baseline (Sprint K body-only) and
writes ``docs/uc3_attachment_intent_results.md``.

Usage (from repo root, Docker PG + Redis up)::

    .venv/Scripts/python.exe scripts/measure_uc3_attachment_intent.py

STOP conditions:
- Wall-clock > 240 seconds for the 25-email fixture (HARD).
- Misclass rate > 40% (relative drop < 30%) — HARD per Sprint O plan §4.

Goal: ≥ 50% relative drop vs the 56% baseline → target ≤ 28% misclass.
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import asyncpg
import yaml
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from aiflow.api.deps import get_pool  # noqa: E402
from aiflow.core.config import UC3AttachmentIntentSettings  # noqa: E402
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
REPORT_PATH = REPO_ROOT / "docs" / "uc3_attachment_intent_results.md"
DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)

HALT_WALL_CLOCK_SECONDS = 240.0
HALT_MISCLASS_CEIL_PCT = 40.0
SPRINT_K_BASELINE_MISCLASS_PCT = 56.0  # docs/uc3_attachment_baseline.md headline


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


async def _cleanup_tenant(pool: asyncpg.Pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1", tenant_id
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM package_associations
                WHERE file_id IN (
                    SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[])
                )
                """,
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])", ids
            )
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )


async def _cleanup_workflow_runs(engine, tenant_id: str) -> None:
    async with engine.begin() as conn:
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


async def _run_one(
    *,
    adapter: EmailSourceAdapter,
    sink: IntakePackageSink,
    classifier: ClassifierService,
    state_repo: StateRepository,
    tenant_id: str,
    schema_labels: list[dict[str, Any]],
    settings: UC3AttachmentIntentSettings,
) -> dict[str, Any]:
    start = time.perf_counter()
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
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if not results:
        return {
            "label": "unknown",
            "confidence": 0.0,
            "method": "no_result",
            "elapsed_ms": elapsed_ms,
        }
    _pkg_id, classification = results[0]
    return {
        "label": classification.label,
        "confidence": float(classification.confidence),
        "method": classification.method,
        "elapsed_ms": elapsed_ms,
    }


async def measure() -> dict[str, Any]:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    fixtures: list[dict[str, Any]] = manifest["fixtures"]
    schema_labels = _load_schema_labels()
    tenant_id = f"uc3-attachment-intent-{uuid4().hex[:8]}"

    pool = await get_pool()
    intake_repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=intake_repo)

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_repo = StateRepository(session_factory)

    classifier = ClassifierService(
        config=ClassifierConfig(
            strategy=ClassificationStrategy.SKLEARN_ONLY, confidence_threshold=0.0
        )
    )
    await classifier.start()

    settings = UC3AttachmentIntentSettings(enabled=True, total_budget_seconds=60.0)

    per_email: list[dict[str, Any]] = []
    wall_start = time.perf_counter()
    try:
        with TemporaryDirectory(prefix="uc3_attachment_intent_") as tmp:
            storage_root = Path(tmp)
            for idx, entry in enumerate(fixtures, 1):
                eml = (FIXTURE_DIR / f"{entry['id']}.eml").read_bytes()
                backend = _FakeImapBackend(eml, uid=idx)
                adapter = EmailSourceAdapter(
                    backend=backend,
                    storage_root=storage_root / entry["id"],
                    tenant_id=tenant_id,
                )
                outcome = await _run_one(
                    adapter=adapter,
                    sink=sink,
                    classifier=classifier,
                    state_repo=state_repo,
                    tenant_id=tenant_id,
                    schema_labels=schema_labels,
                    settings=settings,
                )
                expected = entry["expected_intent"]
                got = outcome["label"]
                per_email.append(
                    {
                        "id": entry["id"],
                        "cohort": entry["cohort"],
                        "category": entry["category"],
                        "expected_intent": expected,
                        "predicted_intent": got,
                        "confidence": outcome["confidence"],
                        "method": outcome["method"],
                        "latency_ms": round(outcome["elapsed_ms"], 2),
                        "correct": got == expected,
                    }
                )
    finally:
        wall_ms = (time.perf_counter() - wall_start) * 1000.0
        await classifier.stop()
        await _cleanup_workflow_runs(engine, tenant_id)
        await _cleanup_tenant(pool, tenant_id)
        await engine.dispose()

    totals = _aggregate(per_email)
    totals["wall_clock_ms"] = round(wall_ms, 2)
    totals["tenant_id"] = tenant_id
    return {"per_email": per_email, "totals": totals}


def _aggregate(per_email: list[dict[str, Any]]) -> dict[str, Any]:
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
        row = by_cohort.setdefault(r["cohort"], {"total": 0, "correct": 0, "miss": 0})
        row["total"] += 1
        if r["correct"]:
            row["correct"] += 1
        else:
            row["miss"] += 1

    boosted = sum(1 for r in per_email if "attachment_rule" in r["method"])
    method_counter: Counter[str] = Counter(r["method"] for r in per_email)

    return {
        "n": n,
        "correct": correct,
        "misclass_pct": round(misclass_pct, 2),
        "boosted_count": boosted,
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "by_cohort": by_cohort,
        "methods": dict(method_counter.most_common()),
    }


def _render_report(result: dict[str, Any]) -> str:
    per = result["per_email"]
    totals = result["totals"]
    baseline_pct = SPRINT_K_BASELINE_MISCLASS_PCT
    abs_drop = baseline_pct - totals["misclass_pct"]
    rel_drop = (abs_drop / baseline_pct * 100.0) if baseline_pct else 0.0
    target_met = totals["misclass_pct"] <= 28.0

    lines: list[str] = []
    lines.append("# UC3 Sprint O — Attachment-Intent Flag-ON Results")
    lines.append("")
    lines.append("> Generated by `scripts/measure_uc3_attachment_intent.py`.")
    lines.append("> Path under test: `scan_and_classify` with")
    lines.append("> `UC3AttachmentIntentSettings(enabled=True)` + S128 rule boost.")
    lines.append("> Baseline source: `docs/uc3_attachment_baseline.md` (Sprint K body-only).")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"- **Misclass rate (flag ON):** {totals['misclass_pct']:.2f}% "
        f"({totals['n'] - totals['correct']}/{totals['n']})"
    )
    lines.append(f"- **Baseline misclass (Sprint K body-only):** {baseline_pct:.2f}%")
    lines.append(f"- **Absolute drop:** {abs_drop:.2f} pts | **Relative drop:** {rel_drop:.2f}%")
    target_str = "PASS" if target_met else "MISS"
    lines.append(f"- **Target ≤ 28% misclass (≥ 50% relative drop):** {target_str}")
    lines.append(f"- **Boosted by attachment rule:** {totals['boosted_count']}/{totals['n']}")
    lines.append(
        f"- **Wall clock:** {totals['wall_clock_ms']:.0f} ms | "
        f"p50 {totals['latency_p50_ms']:.0f} ms | p95 {totals['latency_p95_ms']:.0f} ms"
    )
    lines.append("")

    lines.append("## Per-cohort")
    lines.append("")
    lines.append("| Cohort | Total | Correct | Miss | Misclass % |")
    lines.append("|---|---|---|---|---|")
    for cohort, row in totals["by_cohort"].items():
        cohort_misclass = (row["miss"] / row["total"] * 100.0) if row["total"] else 0.0
        lines.append(
            f"| {cohort} | {row['total']} | {row['correct']} | {row['miss']} | "
            f"{cohort_misclass:.2f}% |"
        )
    lines.append("")

    lines.append("## Per-fixture")
    lines.append("")
    lines.append("| Fixture | Cohort | Expected | Predicted | OK | Conf | Method |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in per:
        ok = "✅" if r["correct"] else "❌"
        lines.append(
            f"| `{r['id']}` | {r['cohort']} | `{r['expected_intent']}` | "
            f"`{r['predicted_intent']}` | {ok} | {r['confidence']:.3f} | {r['method']} |"
        )
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    result = await measure()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_report(result), encoding="utf-8")
    totals = result["totals"]
    print(f"[ok] wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(
        f"[stats] misclass={totals['misclass_pct']:.2f}% "
        f"baseline={SPRINT_K_BASELINE_MISCLASS_PCT}% "
        f"boosted={totals['boosted_count']}/{totals['n']} "
        f"wall={totals['wall_clock_ms']:.0f}ms"
    )
    if totals["wall_clock_ms"] > HALT_WALL_CLOCK_SECONDS * 1000.0:
        print(
            f"[HALT] wall clock {totals['wall_clock_ms']:.0f}ms exceeds "
            f"{HALT_WALL_CLOCK_SECONDS:.0f}s budget",
            file=sys.stderr,
        )
        return 2
    if totals["misclass_pct"] > HALT_MISCLASS_CEIL_PCT:
        print(
            f"[HALT] misclass {totals['misclass_pct']:.2f}% exceeds "
            f"{HALT_MISCLASS_CEIL_PCT:.2f}% ceiling — rule boost insufficient",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
