"""Measure Sprint Q / S137 UC1 invoice_finder golden-path accuracy.

Runs the 10-fixture invoice corpus through the full invoice_processor
pipeline (parse_invoice + extract_invoice_data) via real docling + real
OpenAI, compares extracted fields against the manifest ground-truth,
and writes ``docs/uc1_golden_path_report.md`` with per-field accuracy,
latency p50/p95, and total cost.

Usage (from repo root; Docker PG + OPENAI_API_KEY required)::

    .venv/Scripts/python.exe scripts/measure_uc1_golden_path.py

STOP conditions (HARD, exit 2):
- Wall-clock > 600 s for 10 fixtures.
- Mean cost per invoice > $0.10.
- Overall accuracy < 60% (corpus needs curation).

Target: ≥ 80% overall accuracy, ≥ 90% invoice_number accuracy.
"""

from __future__ import annotations

import asyncio
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env", override=False)

from skills.invoice_processor.workflows.process import (  # noqa: E402
    extract_invoice_data,
    parse_invoice,
)

FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "invoices_sprint_q"
MANIFEST_PATH = FIXTURE_DIR / "manifest.yaml"
REPORT_PATH = REPO_ROOT / "docs" / "uc1_golden_path_report.md"

HALT_WALL_CLOCK_SECONDS = 600.0
HALT_MEAN_COST_USD = 0.10
HALT_ACCURACY_PCT = 60.0

# gpt-4o-mini pricing (USD/M tokens): $0.15 input, $0.60 output.
COST_INPUT_PER_TOKEN = 0.15e-6
COST_OUTPUT_PER_TOKEN = 0.60e-6


def _normalize_number(val: Any) -> float | None:
    """Coerce common invoice-total shapes (str / int / float, with commas)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").replace(" ", "").strip()
    m = re.search(r"[-+]?\d*\.?\d+", s)
    return float(m.group()) if m else None


def _match_scalar(expected: Any, actual: Any) -> bool:
    """Equality comparison for invoice fields, numeric-aware with 2% tolerance."""
    if expected is None or actual is None:
        return expected == actual
    if isinstance(expected, (int, float)):
        a = _normalize_number(actual)
        if a is None:
            return False
        return abs(a - float(expected)) <= max(1.0, abs(float(expected)) * 0.02)
    # String compare: case-insensitive substring or exact after whitespace-norm.
    exp_norm = str(expected).strip().lower()
    act_norm = str(actual).strip().lower()
    if not exp_norm or not act_norm:
        return exp_norm == act_norm
    return exp_norm in act_norm or act_norm in exp_norm


def _score_fixture(expected: dict[str, Any], extracted: dict[str, Any]) -> dict[str, bool]:
    """Return {field: hit} for each expected key."""
    header = extracted.get("header") or {}
    vendor = extracted.get("vendor") or {}
    buyer = extracted.get("buyer") or {}
    totals = extracted.get("totals") or {}

    actual_map = {
        "invoice_number": header.get("invoice_number"),
        "vendor_name": vendor.get("name"),
        "buyer_name": buyer.get("name"),
        "currency": header.get("currency"),
        "issue_date": header.get("issue_date"),
        "due_date": header.get("due_date"),
        "gross_total": totals.get("gross_total"),
    }
    return {k: _match_scalar(expected.get(k), actual_map.get(k)) for k in expected}


async def _run_one(fixture: dict[str, Any]) -> dict[str, Any]:
    pdf_path = FIXTURE_DIR / fixture["pdf"]
    start = time.perf_counter()
    try:
        parse_result = await parse_invoice({"source_path": str(pdf_path)})
        extract_result = await extract_invoice_data(parse_result)
    except Exception as exc:
        return {
            "id": fixture["id"],
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
            "cost_usd": 0.0,
            "accuracy_hits": {k: False for k in fixture["expected"]},
            "confidence": 0.0,
        }
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    files = extract_result.get("files", [])
    if not files or files[0].get("error"):
        return {
            "id": fixture["id"],
            "error": files[0].get("error", "no output") if files else "no files",
            "elapsed_ms": elapsed_ms,
            "cost_usd": 0.0,
            "accuracy_hits": {k: False for k in fixture["expected"]},
            "confidence": 0.0,
        }
    first = files[0]
    in_tokens = first.get("_llm_total_input_tokens", 0)
    out_tokens = first.get("_llm_total_output_tokens", 0)
    cost_usd = round(in_tokens * COST_INPUT_PER_TOKEN + out_tokens * COST_OUTPUT_PER_TOKEN, 6)
    return {
        "id": fixture["id"],
        "cohort": fixture["cohort"],
        "lang": fixture["lang"],
        "elapsed_ms": elapsed_ms,
        "cost_usd": cost_usd,
        "confidence": first.get("extraction_confidence", 0.0),
        "accuracy_hits": _score_fixture(fixture["expected"], first),
        "extracted": {
            "invoice_number": (first.get("header") or {}).get("invoice_number"),
            "vendor_name": (first.get("vendor") or {}).get("name"),
            "buyer_name": (first.get("buyer") or {}).get("name"),
            "currency": (first.get("header") or {}).get("currency"),
            "issue_date": (first.get("header") or {}).get("issue_date"),
            "due_date": (first.get("header") or {}).get("due_date"),
            "gross_total": (first.get("totals") or {}).get("gross_total"),
        },
        "expected": fixture["expected"],
    }


async def measure() -> dict[str, Any]:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    fixtures: list[dict[str, Any]] = manifest["fixtures"]
    results: list[dict[str, Any]] = []
    wall_start = time.perf_counter()
    for fx in fixtures:
        print(f"[run] {fx['id']} ...", flush=True)
        r = await _run_one(fx)
        results.append(r)
        accuracy = sum(1 for v in r["accuracy_hits"].values() if v) / max(
            1, len(r["accuracy_hits"])
        )
        print(f"  accuracy={accuracy:.0%} cost=${r['cost_usd']} latency={r['elapsed_ms']:.0f}ms")
    wall_ms = (time.perf_counter() - wall_start) * 1000.0
    return {"results": results, "wall_clock_ms": round(wall_ms, 2)}


def _aggregate(data: dict[str, Any]) -> dict[str, Any]:
    rows = data["results"]
    n = len(rows)
    latencies = [r["elapsed_ms"] for r in rows]
    costs = [r["cost_usd"] for r in rows]
    confidences = [r["confidence"] for r in rows]

    # Per-field accuracy across all fixtures.
    fields = list(rows[0]["accuracy_hits"].keys())
    per_field: dict[str, dict[str, Any]] = {}
    for f in fields:
        hits = sum(1 for r in rows if r["accuracy_hits"].get(f))
        per_field[f] = {"hits": hits, "total": n, "accuracy_pct": round(hits / n * 100, 2)}

    # Overall accuracy — average across fixtures (each fixture gets hits/fields).
    overall_hits = 0
    overall_total = 0
    for r in rows:
        overall_hits += sum(1 for v in r["accuracy_hits"].values() if v)
        overall_total += len(r["accuracy_hits"])
    overall_accuracy = round(overall_hits / max(1, overall_total) * 100, 2)

    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else (max(latencies) if latencies else 0.0)
    )

    return {
        "n": n,
        "overall_accuracy_pct": overall_accuracy,
        "per_field": per_field,
        "total_cost_usd": round(sum(costs), 6),
        "mean_cost_usd": round(sum(costs) / max(1, n), 6),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "mean_confidence": round(sum(confidences) / max(1, n), 3),
        "wall_clock_ms": data["wall_clock_ms"],
    }


def _render_report(data: dict[str, Any], agg: dict[str, Any]) -> str:
    rows = data["results"]
    lines: list[str] = []
    lines.append("# UC1 Sprint Q — invoice_finder golden-path accuracy")
    lines.append("")
    lines.append("> Generated by `scripts/measure_uc1_golden_path.py`.")
    lines.append(
        "> Path under test: `skills/invoice_processor/workflows/process.py` "
        "(parse_invoice → extract_invoice_data), real docling + real OpenAI."
    )
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"- **Overall accuracy:** {agg['overall_accuracy_pct']:.1f}% "
        f"({sum(1 for r in rows for v in r['accuracy_hits'].values() if v)}/"
        f"{sum(len(r['accuracy_hits']) for r in rows)} fields)"
    )
    lines.append(f"- **Fixtures:** {agg['n']}")
    lines.append(f"- **Mean confidence:** {agg['mean_confidence']:.2%}")
    lines.append(
        f"- **Total cost:** ${agg['total_cost_usd']:.4f}  |  **Mean cost/invoice:** ${agg['mean_cost_usd']:.4f}"
    )
    lines.append(
        f"- **Latency:** p50 {agg['latency_p50_ms']:.0f} ms · p95 {agg['latency_p95_ms']:.0f} ms · "
        f"wall {agg['wall_clock_ms']:.0f} ms"
    )
    lines.append("")

    lines.append("## Per-field accuracy")
    lines.append("")
    lines.append("| Field | Hits | Total | Accuracy |")
    lines.append("|---|---|---|---|")
    for f, info in agg["per_field"].items():
        lines.append(
            f"| `{f}` | {info['hits']} | {info['total']} | **{info['accuracy_pct']:.1f}%** |"
        )
    lines.append("")

    lines.append("## Per-fixture")
    lines.append("")
    lines.append("| Fixture | Cohort | Lang | Hits | Conf | Cost | Latency | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        hits = sum(1 for v in r["accuracy_hits"].values() if v)
        total = len(r["accuracy_hits"])
        notes = r.get("error", "") or ",".join(k for k, v in r["accuracy_hits"].items() if not v)
        lines.append(
            f"| `{r['id']}` | {r.get('cohort', '—')} | {r.get('lang', '—')} "
            f"| {hits}/{total} | {r['confidence']:.0%} | ${r['cost_usd']:.4f} "
            f"| {r['elapsed_ms']:.0f}ms | {notes[:60]} |"
        )
    lines.append("")

    lines.append("## HITL eligible (confidence < 0.6)")
    lines.append("")
    hitl = [r for r in rows if r["confidence"] < 0.6]
    if not hitl:
        lines.append("_(none — all invoices above the HITL threshold)_")
    else:
        for r in hitl:
            lines.append(f"- `{r['id']}` — confidence {r['confidence']:.0%}")
    lines.append("")

    return "\n".join(lines)


async def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("[error] OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    if not MANIFEST_PATH.exists():
        print(f"[error] manifest missing at {MANIFEST_PATH}", file=sys.stderr)
        return 2
    data = await measure()
    agg = _aggregate(data)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_report(data, agg), encoding="utf-8")
    print(f"[ok] wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(
        f"[stats] accuracy={agg['overall_accuracy_pct']}% mean_cost=${agg['mean_cost_usd']} "
        f"wall={agg['wall_clock_ms']:.0f}ms"
    )
    if agg["wall_clock_ms"] > HALT_WALL_CLOCK_SECONDS * 1000.0:
        print(
            f"[HALT] wall clock {agg['wall_clock_ms']:.0f}ms exceeds "
            f"{HALT_WALL_CLOCK_SECONDS:.0f}s",
            file=sys.stderr,
        )
        return 2
    if agg["mean_cost_usd"] > HALT_MEAN_COST_USD:
        print(
            f"[HALT] mean cost ${agg['mean_cost_usd']} exceeds ${HALT_MEAN_COST_USD}",
            file=sys.stderr,
        )
        return 2
    if agg["overall_accuracy_pct"] < HALT_ACCURACY_PCT:
        print(
            f"[HALT] accuracy {agg['overall_accuracy_pct']}% below "
            f"{HALT_ACCURACY_PCT}% floor — corpus curation needed",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
