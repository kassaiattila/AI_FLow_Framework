#!/usr/bin/env python
"""Cost baseline report generator (B5.3).

Aggregates the ``cost_records`` table and emits a Markdown report with:
- Global summary (runs, total $, avg $/run, cheapest/priciest)
- Per-service breakdown (step_name → runs, $, avg, share)
- Per-model breakdown (model → requests, tokens, $)
- Daily trend (last 7 days)
- Warnings (services > $0.10 / run average, models > $0.50 / request)
- Recommendations (gpt-4o → gpt-4o-mini candidates)
- Langfuse integration notes

Usage:
    .venv/Scripts/python scripts/cost_baseline.py [--output 01_PLAN/COST_BASELINE_REPORT.md]
                                                  [--since 2026-04-01]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import asyncpg
import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)

load_dotenv(Path(__file__).parent.parent / ".env")


# ---------------------------------------------------------------------------
# Thresholds (edit here if the team wants a different alert level)
# ---------------------------------------------------------------------------

SERVICE_RUN_WARNING_USD = 0.10
MODEL_REQUEST_WARNING_USD = 0.50
GPT_4O_REPLACEMENT_BREAKEVEN_USD = 0.01  # recommend gpt-4o-mini if avg > this


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _connect() -> asyncpg.Connection:
    url = os.getenv(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    ).replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url)


async def fetch_cost_records(
    conn: asyncpg.Connection,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    if since:
        query = (
            "SELECT workflow_run_id, step_name, model, provider, "
            "input_tokens, output_tokens, cost_usd, recorded_at "
            "FROM cost_records WHERE recorded_at >= $1 "
            "ORDER BY recorded_at DESC"
        )
        rows = await conn.fetch(query, since)
    else:
        rows = await conn.fetch(
            "SELECT workflow_run_id, step_name, model, provider, "
            "input_tokens, output_tokens, cost_usd, recorded_at "
            "FROM cost_records ORDER BY recorded_at DESC"
        )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def aggregate_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "total_records": 0,
            "total_runs": 0,
            "total_usd": 0.0,
            "avg_usd_per_run": 0.0,
            "max_run": None,
            "min_run": None,
        }

    run_totals: dict[str, float] = defaultdict(float)
    total_usd = 0.0
    for r in records:
        cost = _to_float(r["cost_usd"])
        total_usd += cost
        run_totals[str(r["workflow_run_id"])] += cost

    max_run = max(run_totals.items(), key=lambda kv: kv[1]) if run_totals else None
    min_run = min(run_totals.items(), key=lambda kv: kv[1]) if run_totals else None

    return {
        "total_records": len(records),
        "total_runs": len(run_totals),
        "total_usd": total_usd,
        "avg_usd_per_run": total_usd / len(run_totals) if run_totals else 0.0,
        "max_run": max_run,
        "min_run": min_run,
    }


def aggregate_per_service(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate by step_name (our closest proxy for 'service')."""
    by_service: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"run_ids": set(), "requests": 0, "total_usd": 0.0}
    )
    total_usd = sum(_to_float(r["cost_usd"]) for r in records)

    for r in records:
        name = r.get("step_name") or "(unknown)"
        by_service[name]["run_ids"].add(str(r["workflow_run_id"]))
        by_service[name]["requests"] += 1
        by_service[name]["total_usd"] += _to_float(r["cost_usd"])

    result = []
    for name, agg in by_service.items():
        runs = len(agg["run_ids"])
        total = agg["total_usd"]
        share = (total / total_usd * 100.0) if total_usd else 0.0
        result.append(
            {
                "service": name,
                "runs": runs,
                "requests": agg["requests"],
                "total_usd": total,
                "avg_usd_per_run": (total / runs) if runs else 0.0,
                "share_pct": share,
            }
        )
    result.sort(key=lambda x: x["total_usd"], reverse=True)
    return result


def aggregate_per_model(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_usd": 0.0,
        }
    )

    for r in records:
        key = r.get("model") or "(unknown)"
        by_model[key]["requests"] += 1
        by_model[key]["input_tokens"] += int(r.get("input_tokens") or 0)
        by_model[key]["output_tokens"] += int(r.get("output_tokens") or 0)
        by_model[key]["total_usd"] += _to_float(r["cost_usd"])

    result = []
    for name, agg in by_model.items():
        reqs = agg["requests"]
        result.append(
            {
                "model": name,
                "requests": reqs,
                "input_tokens": agg["input_tokens"],
                "output_tokens": agg["output_tokens"],
                "total_usd": agg["total_usd"],
                "avg_per_request": (agg["total_usd"] / reqs) if reqs else 0.0,
            }
        )
    result.sort(key=lambda x: x["total_usd"], reverse=True)
    return result


def aggregate_per_day(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": set(), "total_usd": 0.0})
    for r in records:
        recorded_at: datetime = r["recorded_at"]
        day = recorded_at.date().isoformat()
        by_day[day]["runs"].add(str(r["workflow_run_id"]))
        by_day[day]["total_usd"] += _to_float(r["cost_usd"])

    result = [
        {"date": day, "runs": len(agg["runs"]), "total_usd": agg["total_usd"]}
        for day, agg in by_day.items()
    ]
    result.sort(key=lambda x: x["date"], reverse=True)
    return result[:7]


def compute_warnings(
    per_service: list[dict[str, Any]],
    per_model: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []

    for svc in per_service:
        if svc["avg_usd_per_run"] > SERVICE_RUN_WARNING_USD:
            warnings.append(
                f"- `{svc['service']}`: ${svc['avg_usd_per_run']:.4f} per run "
                f"(threshold ${SERVICE_RUN_WARNING_USD:.2f}) — investigate."
            )

    for mdl in per_model:
        if mdl["avg_per_request"] > MODEL_REQUEST_WARNING_USD:
            warnings.append(
                f"- `{mdl['model']}`: ${mdl['avg_per_request']:.4f} per request "
                f"(threshold ${MODEL_REQUEST_WARNING_USD:.2f}) — evaluate cheaper model."
            )

    return warnings or ["- _No warnings — costs are within thresholds._"]


def compute_recommendations(per_model: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []

    for mdl in per_model:
        name = str(mdl["model"])
        if name.endswith("gpt-4o") and mdl["avg_per_request"] > GPT_4O_REPLACEMENT_BREAKEVEN_USD:
            savings_pct = 85  # empirical: gpt-4o-mini is ~15% of gpt-4o price
            recommendations.append(
                f"- Replace `{name}` with `gpt-4o-mini` where accuracy allows — "
                f"potential {savings_pct}% cost reduction "
                f"(${mdl['total_usd']:.4f} → ~${mdl['total_usd'] * 0.15:.4f})."
            )

    return recommendations or [
        "- _No obvious downgrades — all models already chosen for their use case._"
    ]


# ---------------------------------------------------------------------------
# Markdown report formatter
# ---------------------------------------------------------------------------


def _fmt_usd(value: float) -> str:
    return f"${value:.6f}" if value < 0.01 else f"${value:.4f}"


def _fmt_tokens(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_markdown_report(
    records: list[dict[str, Any]],
    aggregations: dict[str, Any],
    since: datetime | None,
) -> str:
    now = datetime.now(UTC)
    summary = aggregations["summary"]
    per_service = aggregations["per_service"]
    per_model = aggregations["per_model"]
    per_day = aggregations["per_day"]
    warnings = aggregations["warnings"]
    recommendations = aggregations["recommendations"]

    lines: list[str] = []
    lines.append("# AIFlow Cost Baseline Report")
    lines.append("")
    lines.append(f"> Generated: {now.isoformat(timespec='seconds')}")
    lines.append(
        f"> Query range: {'all records' if since is None else 'since ' + since.isoformat()}"
    )
    lines.append("> Branch: `feature/v1.3.0-service-excellence`")
    lines.append("> Source: `cost_records` table (AIFlow PostgreSQL)")
    lines.append("")

    # --- Summary ---
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total records:** {summary['total_records']}")
    lines.append(f"- **Distinct workflow runs:** {summary['total_runs']}")
    lines.append(f"- **Total cost:** {_fmt_usd(summary['total_usd'])}")
    lines.append(f"- **Average cost / run:** {_fmt_usd(summary['avg_usd_per_run'])}")
    if summary["max_run"]:
        run_id, cost = summary["max_run"]
        lines.append(f"- **Most expensive run:** `{run_id[:8]}…` — {_fmt_usd(cost)}")
    if summary["min_run"]:
        run_id, cost = summary["min_run"]
        lines.append(f"- **Cheapest run:** `{run_id[:8]}…` — {_fmt_usd(cost)}")
    lines.append("")

    # --- Per-service ---
    lines.append("## Per-Service Breakdown")
    lines.append("")
    if per_service:
        lines.append("| Service (step) | Runs | Requests | Total USD | Avg/run | % of total |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for s in per_service:
            lines.append(
                f"| `{s['service']}` | {s['runs']} | {s['requests']} | "
                f"{_fmt_usd(s['total_usd'])} | {_fmt_usd(s['avg_usd_per_run'])} | "
                f"{s['share_pct']:.1f}% |"
            )
    else:
        lines.append("_No service-level data available._")
    lines.append("")

    # --- Per-model ---
    lines.append("## Per-Model Breakdown")
    lines.append("")
    if per_model:
        lines.append(
            "| Model | Requests | Input tokens | Output tokens | Total USD | Avg/request |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|")
        for m in per_model:
            lines.append(
                f"| `{m['model']}` | {m['requests']} | {_fmt_tokens(m['input_tokens'])} | "
                f"{_fmt_tokens(m['output_tokens'])} | {_fmt_usd(m['total_usd'])} | "
                f"{_fmt_usd(m['avg_per_request'])} |"
            )
    else:
        lines.append("_No model-level data available._")
    lines.append("")

    # --- Daily trend ---
    lines.append("## Daily Trend (last 7 days)")
    lines.append("")
    if per_day:
        lines.append("| Date | Runs | Total USD |")
        lines.append("|---|---:|---:|")
        for d in per_day:
            lines.append(f"| {d['date']} | {d['runs']} | {_fmt_usd(d['total_usd'])} |")
    else:
        lines.append("_No daily trend data available._")
    lines.append("")

    # --- Warnings ---
    lines.append("## Warnings")
    lines.append("")
    lines.extend(warnings)
    lines.append("")

    # --- Recommendations ---
    lines.append("## Recommendations")
    lines.append("")
    lines.extend(recommendations)
    lines.append("")

    # --- Langfuse integration ---
    lines.append("## Langfuse Integration")
    lines.append("")
    lines.append(
        "- **Local source of truth:** `cost_records` (populated by "
        "`src/aiflow/observability/cost_tracker.py`)."
    )
    lines.append(
        "- **Langfuse cloud:** enable with `AIFLOW_LANGFUSE__ENABLED=true` + "
        "`PUBLIC_KEY` / `SECRET_KEY` env vars. Each step emits a trace span "
        "carrying input / output tokens and model name, which Langfuse "
        "converts to cost via its own pricing table."
    )
    lines.append(
        "- **Cross-checking:** query Langfuse via the v4 SDK "
        "(`langfuse.api.traces.list`) and join by `run_id` to detect drift "
        "between the local `cost_records` sum and the cloud trace "
        "aggregation. Delta > 5% → investigate pricing mismatch."
    )
    lines.append(
        "- **Dashboards:** the /costs admin UI page already visualises "
        "`cost_records` via `/api/v1/costs/summary` and "
        "`/api/v1/costs/breakdown` — Langfuse Cloud dashboards complement "
        "this with historical trace-level drill-down."
    )
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"_Generated by `scripts/cost_baseline.py` at {now.isoformat(timespec='seconds')}_"
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate cost baseline Markdown report from cost_records table."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("01_PLAN") / "COST_BASELINE_REPORT.md",
        help="Target markdown path",
    )
    parser.add_argument(
        "--since",
        "-s",
        type=str,
        default=None,
        help="Only include records since this ISO-8601 date (e.g. 2026-04-01).",
    )
    return parser.parse_args()


async def _run(output: Path, since: datetime | None) -> int:
    conn = await _connect()
    try:
        records = await fetch_cost_records(conn, since=since)
    finally:
        await conn.close()

    logger.info("cost_baseline.fetched", records=len(records))

    per_service = aggregate_per_service(records)
    per_model = aggregate_per_model(records)
    aggregations = {
        "summary": aggregate_summary(records),
        "per_service": per_service,
        "per_model": per_model,
        "per_day": aggregate_per_day(records),
        "warnings": compute_warnings(per_service, per_model),
        "recommendations": compute_recommendations(per_model),
    }

    markdown = format_markdown_report(records, aggregations, since)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")

    logger.info(
        "cost_baseline.done",
        output=str(output),
        records=len(records),
        runs=aggregations["summary"]["total_runs"],
        total_usd=round(aggregations["summary"]["total_usd"], 6),
    )
    print(
        f"Wrote {output} — "
        f"{aggregations['summary']['total_records']} records, "
        f"{aggregations['summary']['total_runs']} runs, "
        f"${aggregations['summary']['total_usd']:.4f} total."
    )
    return 0


def main() -> None:
    args = _parse_args()
    since: datetime | None = None
    if args.since:
        since = datetime.fromisoformat(args.since)
        if since.tzinfo is None:
            since = since.replace(tzinfo=UTC)

    rc = asyncio.run(_run(output=args.output, since=since))
    sys.exit(rc)


if __name__ == "__main__":
    main()
