"""Sprint V SV-5 — measure document recognizer top-1 doctype accuracy.

Operator + CI tool. Walks ``data/fixtures/doc_recognizer/<doctype>/`` and
runs each fixture through the rule-engine classifier (no LLM call —
hermetic + fast). Reports per-doctype top-1 accuracy + overall +
per-doctype false-positive rate.

Usage::

    .venv/Scripts/python.exe scripts/measure_doc_recognizer_accuracy.py
    .venv/Scripts/python.exe scripts/measure_doc_recognizer_accuracy.py --output json
    .venv/Scripts/python.exe scripts/measure_doc_recognizer_accuracy.py --doctypes hu_invoice,hu_id_card

Output formats: ``text`` (human-readable), ``json`` (CI artifact),
``jsonl`` (per-fixture rows).

Sprint V SV-5 SLO targets (from 119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md
§2 SV-5 + §3 gate matrix):
* hu_invoice ≥ 90% top-1
* hu_id_card ≥ 80% top-1
* pdf_contract ≥ 80% top-1
* hu_address_card ≥ 70% top-1 (best-effort)
* eu_passport ≥ 70% top-1 (best-effort)
* Cross-doctype top-1 ≥ 90% on full corpus (false-positive ≤ 4%)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from scripts._common import argparse_output, write_output  # noqa: E402

from aiflow.services.document_recognizer.classifier import (  # noqa: E402
    ClassifierInput,
    classify_doctype,
)
from aiflow.services.document_recognizer.registry import DocTypeRegistry  # noqa: E402

FIXTURES_ROOT = REPO_ROOT / "data" / "fixtures" / "doc_recognizer"
DOCTYPES_ROOT = REPO_ROOT / "data" / "doctypes"


def _scan_fixtures(doctypes: list[str] | None) -> dict[str, list[Path]]:
    """Return {doctype_name: [fixture_path, ...]}."""
    if not FIXTURES_ROOT.exists():
        return {}
    out: dict[str, list[Path]] = {}
    for type_dir in sorted(FIXTURES_ROOT.iterdir()):
        if not type_dir.is_dir():
            continue
        if doctypes and type_dir.name not in doctypes:
            continue
        files = sorted(f for f in type_dir.iterdir() if f.is_file() and not f.name.startswith("."))
        if files:
            out[type_dir.name] = files
    return out


def _load_fixture_text(path: Path) -> str:
    """Read a fixture as text. Synthetic fixtures are .txt; binaries return empty."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".eml"}:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    # PDFs / DOCX / images — operators add fixtures via real parser routing
    # in a future iteration. SV-5 ships text-only synthetic fixtures.
    return ""


def measure(doctypes_filter: list[str] | None = None) -> dict:
    """Run the measurement and return a structured payload."""
    registry = DocTypeRegistry(bootstrap_dir=DOCTYPES_ROOT)
    descriptors = registry.list_doctypes()
    fixtures = _scan_fixtures(doctypes_filter)

    per_doctype: dict[str, dict] = {}
    per_fixture: list[dict] = []
    total_correct = 0
    total_fixtures = 0

    for expected_type, paths in fixtures.items():
        correct = 0
        false_positive_for_others = 0
        for path in paths:
            text = _load_fixture_text(path)
            ctx = ClassifierInput(text=text, filename=path.name)
            match = classify_doctype(descriptors, ctx)
            top1 = match.doc_type if match else None
            top1_conf = match.confidence if match else 0.0
            is_correct = top1 == expected_type
            if is_correct:
                correct += 1
            elif top1 is not None:
                false_positive_for_others += 1
            per_fixture.append(
                {
                    "expected": expected_type,
                    "fixture": path.name,
                    "top1": top1,
                    "top1_confidence": round(top1_conf, 4),
                    "correct": is_correct,
                }
            )
            total_fixtures += 1
            if is_correct:
                total_correct += 1
        accuracy = correct / len(paths) if paths else 0.0
        per_doctype[expected_type] = {
            "fixture_count": len(paths),
            "correct": correct,
            "accuracy": round(accuracy, 4),
            "false_positive": false_positive_for_others,
        }

    overall_accuracy = total_correct / total_fixtures if total_fixtures else 0.0
    return {
        "fixture_count": total_fixtures,
        "doctype_count": len(per_doctype),
        "overall_accuracy": round(overall_accuracy, 4),
        "per_doctype": per_doctype,
        "per_fixture": per_fixture,
        "slo_targets": {
            "hu_invoice": 0.90,
            "hu_id_card": 0.80,
            "pdf_contract": 0.80,
            "hu_address_card": 0.70,
            "eu_passport": 0.70,
            "overall": 0.90,
        },
    }


def _format_text(report: dict) -> str:
    lines = [
        "=== Document Recognizer Accuracy Report ===",
        f"Fixtures: {report['fixture_count']} across {report['doctype_count']} doctypes",
        f"Overall top-1 accuracy: {report['overall_accuracy'] * 100:.1f}%",
        "",
        "Per-doctype:",
    ]
    for name, stats in sorted(report["per_doctype"].items()):
        slo = report["slo_targets"].get(name, 0.0)
        gate = "PASS" if stats["accuracy"] >= slo else "FAIL"
        lines.append(
            f"  [{gate}] {name:24s} accuracy={stats['accuracy'] * 100:5.1f}% "
            f"({stats['correct']}/{stats['fixture_count']})  SLO>={slo * 100:.0f}%  "
            f"FP_other={stats['false_positive']}"
        )
    if report["fixture_count"] == 0:
        lines.append("")
        lines.append(
            "[warn] No fixtures found at data/fixtures/doc_recognizer/. "
            "Operators add per-doctype starter fixtures (.txt synthetic) here."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--doctypes",
        type=str,
        default=None,
        help="Comma-separated doctype filter (e.g. 'hu_invoice,pdf_contract').",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any per-doctype accuracy is below its SLO target.",
    )
    argparse_output(parser, default_mode="text")
    args = parser.parse_args(argv)

    doctype_filter = (
        [s.strip() for s in args.doctypes.split(",") if s.strip()] if args.doctypes else None
    )

    report = measure(doctype_filter)

    if args.output == "text":
        write_output("text", args.output_path, _format_text(report))
    elif args.output == "jsonl":
        write_output("jsonl", args.output_path, report["per_fixture"])
    else:
        write_output("json", args.output_path, report)

    if args.strict:
        # Exit non-zero on any below-SLO doctype
        for name, stats in report["per_doctype"].items():
            slo = report["slo_targets"].get(name, 0.0)
            if stats["accuracy"] < slo:
                print(
                    f"[strict] {name} accuracy {stats['accuracy'] * 100:.1f}% < SLO {slo * 100:.0f}%",
                    file=sys.stderr,
                )
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
