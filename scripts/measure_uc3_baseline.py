"""Measure the Sprint K UC3 classifier baseline on the Sprint O fixture.

S126 discovery. Runs every fixture email in
``data/fixtures/emails_sprint_o/`` through the real ``scan_and_classify``
orchestrator (EmailSourceAdapter → IntakePackageSink → ClassifierService
→ StateRepository) against a live Docker Postgres, using the production
Sprint K v1 intent schema and the keyword-only ``SKLEARN_ONLY`` strategy.

This is the **pre-Sprint O** baseline — the classifier sees only the email
body / subject. Attachments are persisted through the sink but their text
is never read. S127 adds that.

Output: ``docs/uc3_attachment_baseline.md`` (overwritten on each run).

Usage (from repo root, Docker PG + Redis up):

    .venv/Scripts/python.exe scripts/measure_uc3_baseline.py

STOP conditions (HALT + exit 2 if hit):
- Script wall-clock > 180 seconds for the 25-email fixture.
- Fixture misclass rate < 15% (sprint value unproven — hand back to user).

No LLM calls are made. Pure keyword scoring baseline.
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from collections import Counter
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import asyncpg
import structlog
import yaml
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from aiflow.api.deps import get_pool  # noqa: E402
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

logger = structlog.get_logger("measure_uc3_baseline")

FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "emails_sprint_o"
MANIFEST_PATH = FIXTURE_DIR / "manifest.yaml"
INTENT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "email_intent_processor" / "schemas" / "v1" / "intents.json"
)
REPORT_PATH = REPO_ROOT / "docs" / "uc3_attachment_baseline.md"
DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)

HALT_MISCLASS_FLOOR_PCT = 15.0
HALT_WALL_CLOCK_SECONDS = 180.0


# ---------------------------------------------------------------------------
# In-memory IMAP backend (single-email) — matches the fake used in
# tests/integration/services/email_connector/test_scan_and_classify.py.
# ---------------------------------------------------------------------------


class _FakeImapBackend(ImapBackendProtocol):
    def __init__(self, raw_bytes: bytes, uid: int = 1) -> None:
        self._inbox = [(uid, raw_bytes)]
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


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------


def _load_schema_labels() -> list[dict[str, Any]]:
    """Load the Sprint K v1 intent schema and flatten HU+EN keywords."""
    data = json.loads(INTENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for intent in data["intents"]:
        keywords: list[str] = []
        keywords.extend(intent.get("keywords_hu", []))
        keywords.extend(intent.get("keywords_en", []))
        out.append(
            {
                "id": intent["id"],
                "display_name": intent.get("display_name", intent["id"]),
                "description": intent.get("description", ""),
                "keywords": keywords,
                "examples": intent.get("examples", []),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Attachment mime profile
# ---------------------------------------------------------------------------


def _profile_mime(raw: bytes) -> list[str]:
    """Return attachment mime types, excluding the body-only intake marker."""
    msg: Message = message_from_bytes(raw)
    mimes: list[str] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if not filename:
            continue
        # Body-only fixtures carry a tiny note.txt to satisfy intake's
        # association_mode CHECK constraint — not a real attachment signal.
        if filename == "note.txt":
            continue
        mimes.append(part.get_content_type())
    return mimes


# ---------------------------------------------------------------------------
# DB cleanup
# ---------------------------------------------------------------------------


async def _cleanup_tenant(pool: asyncpg.Pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1",
            tenant_id,
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
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])",
                ids,
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


# ---------------------------------------------------------------------------
# Core measurement loop
# ---------------------------------------------------------------------------


async def _run_one(
    *,
    adapter: EmailSourceAdapter,
    sink: IntakePackageSink,
    classifier: ClassifierService,
    state_repo: StateRepository,
    tenant_id: str,
    schema_labels: list[dict[str, Any]],
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
    tenant_id = f"uc3-baseline-{uuid4().hex[:8]}"

    pool = await get_pool()
    intake_repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=intake_repo)

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_repo = StateRepository(session_factory)

    classifier = ClassifierService(
        config=ClassifierConfig(
            strategy=ClassificationStrategy.SKLEARN_ONLY,
            confidence_threshold=0.0,
        )
    )
    await classifier.start()

    per_email: list[dict[str, Any]] = []
    wall_start = time.perf_counter()

    try:
        with TemporaryDirectory(prefix="uc3_baseline_") as tmp:
            storage_root = Path(tmp)
            for idx, entry in enumerate(fixtures, 1):
                eml_path = FIXTURE_DIR / f"{entry['id']}.eml"
                raw = eml_path.read_bytes()
                backend = _FakeImapBackend(raw, uid=idx)
                adapter = EmailSourceAdapter(
                    backend=backend,
                    storage_root=storage_root / entry["id"],
                    tenant_id=tenant_id,
                )
                mimes = _profile_mime(raw)
                try:
                    outcome = await _run_one(
                        adapter=adapter,
                        sink=sink,
                        classifier=classifier,
                        state_repo=state_repo,
                        tenant_id=tenant_id,
                        schema_labels=schema_labels,
                    )
                except Exception as exc:  # pragma: no cover — telemetry path
                    logger.error(
                        "uc3_baseline.fixture_error",
                        fixture=entry["id"],
                        error=str(exc),
                    )
                    outcome = {
                        "label": "error",
                        "confidence": 0.0,
                        "method": f"error:{type(exc).__name__}",
                        "elapsed_ms": 0.0,
                    }
                expected = entry["expected_intent"]
                got = outcome["label"]
                correct = got == expected
                per_email.append(
                    {
                        "id": entry["id"],
                        "subject": entry["subject"],
                        "cohort": entry["cohort"],
                        "category": entry["category"],
                        "lang": entry["lang"],
                        "attachment": entry["attachment"],
                        "attachment_mimes": mimes,
                        "expected_intent": expected,
                        "predicted_intent": got,
                        "confidence": outcome["confidence"],
                        "method": outcome["method"],
                        "latency_ms": round(outcome["elapsed_ms"], 2),
                        "correct": correct,
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
    misclassified = n - correct
    misclass_rate = (misclassified / n * 100.0) if n else 0.0

    latencies = [r["latency_ms"] for r in per_email]
    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else (max(latencies) if latencies else 0.0)
    )

    by_category: dict[str, dict[str, int]] = {}
    for r in per_email:
        row = by_category.setdefault(r["category"], {"total": 0, "correct": 0, "miss": 0})
        row["total"] += 1
        if r["correct"]:
            row["correct"] += 1
        else:
            row["miss"] += 1

    by_cohort: dict[str, dict[str, int]] = {}
    for r in per_email:
        row = by_cohort.setdefault(r["cohort"], {"total": 0, "correct": 0, "miss": 0})
        row["total"] += 1
        if r["correct"]:
            row["correct"] += 1
        else:
            row["miss"] += 1

    manual_review_like = sum(1 for r in per_email if r["predicted_intent"] in {"unknown", "error"})
    manual_review_rate = (manual_review_like / n * 100.0) if n else 0.0

    mime_counter: Counter[str] = Counter()
    for r in per_email:
        for m in r["attachment_mimes"]:
            mime_counter[m] += 1

    return {
        "n": n,
        "correct": correct,
        "misclassified": misclassified,
        "misclass_rate_pct": round(misclass_rate, 2),
        "manual_review_like": manual_review_like,
        "manual_review_rate_pct": round(manual_review_rate, 2),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "by_category": by_category,
        "by_cohort": by_cohort,
        "mime_profile": dict(mime_counter.most_common()),
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def _render_report(result: dict[str, Any]) -> str:
    per_email = result["per_email"]
    totals = result["totals"]

    lines: list[str] = []
    lines.append("# UC3 Sprint O — Baseline Misclassification Report")
    lines.append("")
    lines.append("> Generated by `scripts/measure_uc3_baseline.py`.")
    lines.append(
        f"> Fixture: `data/fixtures/emails_sprint_o/` (25 `.eml`). Tenant: `{totals['tenant_id']}`."
    )
    lines.append(
        "> Classifier: `ClassifierService` strategy "
        "`SKLEARN_ONLY` (keyword-only, body + subject). "
        "No LLM calls."
    )
    lines.append(
        "> Schema: `skills/email_intent_processor/schemas/v1/intents.json` "
        "(12 intents, HU+EN keyword union)."
    )
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"- **Misclassification rate: {totals['misclass_rate_pct']:.2f}%** "
        f"({totals['misclassified']}/{totals['n']})"
    )
    lines.append(
        f"- Manual-review-like (unknown/error): {totals['manual_review_rate_pct']:.2f}% "
        f"({totals['manual_review_like']}/{totals['n']})"
    )
    lines.append(
        f"- Latency p50 / p95: {totals['latency_p50_ms']:.2f} ms / {totals['latency_p95_ms']:.2f} ms"
    )
    lines.append(f"- Wall clock: {totals['wall_clock_ms']:.0f} ms total for {totals['n']} emails")
    lines.append("")
    floor = HALT_MISCLASS_FLOOR_PCT
    if totals["misclass_rate_pct"] < floor:
        lines.append(
            f"> **HALT** — baseline misclass rate {totals['misclass_rate_pct']:.2f}% "
            f"< {floor:.0f}% floor. Sprint O value unproven."
        )
    else:
        lines.append(
            f"> **GATE PASS** — {totals['misclass_rate_pct']:.2f}% ≥ {floor:.0f}% "
            f"floor. Proceed to S127."
        )
    lines.append("")

    lines.append("## By category")
    lines.append("")
    lines.append("| Category | Total | Correct | Miss | Miss %  |")
    lines.append("|----------|------:|--------:|-----:|--------:|")
    for cat, row in sorted(totals["by_category"].items()):
        miss_pct = (row["miss"] / row["total"] * 100.0) if row["total"] else 0.0
        lines.append(
            f"| {cat} | {row['total']} | {row['correct']} | {row['miss']} | {miss_pct:.2f}% |"
        )
    lines.append("")

    lines.append("## By cohort")
    lines.append("")
    lines.append("| Cohort | Total | Correct | Miss | Miss % |")
    lines.append("|--------|------:|--------:|-----:|-------:|")
    for cohort, row in sorted(totals["by_cohort"].items()):
        miss_pct = (row["miss"] / row["total"] * 100.0) if row["total"] else 0.0
        lines.append(
            f"| {cohort} | {row['total']} | {row['correct']} | {row['miss']} | {miss_pct:.2f}% |"
        )
    lines.append("")

    lines.append("## Attachment mime profile")
    lines.append("")
    if totals["mime_profile"]:
        lines.append("| Mime | Count |")
        lines.append("|------|------:|")
        for mime, cnt in totals["mime_profile"].items():
            lines.append(f"| `{mime}` | {cnt} |")
    else:
        lines.append("_No attachments across the fixture (unexpected)._")
    lines.append("")

    lines.append("## Per-email detail")
    lines.append("")
    lines.append("| ID | Cohort | Expected | Predicted | OK | Conf | Latency (ms) | Method |")
    lines.append("|----|--------|----------|-----------|:--:|-----:|-------------:|--------|")
    for r in per_email:
        ok_mark = "✅" if r["correct"] else "❌"
        lines.append(
            f"| `{r['id']}` | {r['cohort']} | `{r['expected_intent']}` | "
            f"`{r['predicted_intent']}` | {ok_mark} | "
            f"{r['confidence']:.3f} | {r['latency_ms']:.2f} | {r['method']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- `SKLEARN_ONLY` strategy means the classifier's body-keyword score is "
        "unmerged with any LLM signal. This matches the Sprint K default "
        "`confidence_threshold=0.6` hybrid_llm path's fast-path leg — miss here "
        "predicts a miss or an LLM correction in production. The Sprint O "
        "extractor attacks both legs."
    )
    lines.append(
        "- `method == keywords_no_match` rows represent emails where no intent "
        "had a single keyword hit; production routes these to MANUAL_REVIEW."
    )
    lines.append("- Latency here excludes docling / Azure DI — those are S127 costs.")
    lines.append("")
    return "\n".join(lines) + "\n"


async def _main() -> int:
    result = await measure()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_report(result), encoding="utf-8")
    wall_s = result["totals"]["wall_clock_ms"] / 1000.0
    misclass = result["totals"]["misclass_rate_pct"]
    n = result["totals"]["n"]
    correct = result["totals"]["correct"]
    print(
        f"wrote {REPORT_PATH} | misclass={misclass:.2f}% ({n - correct}/{n}) | wall={wall_s:.2f}s"
    )
    if wall_s > HALT_WALL_CLOCK_SECONDS:
        print(
            f"HALT: wall-clock {wall_s:.2f}s > {HALT_WALL_CLOCK_SECONDS:.0f}s floor",
            file=sys.stderr,
        )
        return 2
    if misclass < HALT_MISCLASS_FLOOR_PCT:
        print(
            f"HALT: misclass {misclass:.2f}% < {HALT_MISCLASS_FLOOR_PCT:.0f}% floor",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
