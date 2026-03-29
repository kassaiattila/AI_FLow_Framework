"""Invoice Processor skill - standalone CLI entry point.

Usage:
    python -m skills.invoice_processor ingest --source "./Szamlak/Bejovo/2021/"
    python -m skills.invoice_processor ingest --source invoice.pdf --direction incoming
    python -m skills.invoice_processor ingest --source "./Szamlak/" --direction auto --output ./export/
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def cmd_ingest(args: argparse.Namespace) -> None:
    """Process invoices from source path."""
    from aiflow.engine.skill_runner import SkillRunner
    from skills.invoice_processor.workflows.process import (
        parse_invoice,
        classify_invoice,
        extract_invoice_data,
        validate_invoice,
        store_invoice,
        export_invoice,
    )

    runner = SkillRunner.from_env(
        default_model="openai/gpt-4o",
        prompt_dirs=[Path(__file__).parent / "prompts"],
    )

    print("=" * 60)
    print("Invoice Processor - Szamla feldolgozo")
    print("=" * 60)
    print(f"Source: {args.source}")
    print(f"Direction: {args.direction}")
    print()

    steps = [parse_invoice, classify_invoice, extract_invoice_data, validate_invoice]
    if not args.no_store:
        steps.append(store_invoice)
    steps.append(export_invoice)

    result = await runner.run_steps(
        steps,
        {
            "source_path": args.source,
            "direction": args.direction,
            "output_dir": args.output,
            "format": args.format,
        },
    )

    # Display results
    files = result.get("files", [])
    summary = result.get("export_summary", {})
    print("-" * 60)
    print("RESULTS")
    print("-" * 60)
    print(f"  Feldolgozott: {summary.get('total_invoices', 0)} szamla")
    print(f"  Tetelek:      {summary.get('total_line_items', 0)} db")
    print(f"  Brutto ossz:  {summary.get('total_gross', 0):,.0f} Ft")
    print()

    for f in files:
        if f.get("error"):
            print(f"  HIBA: {f.get('filename')} - {f.get('error')}")
            continue
        valid = f.get("validation", {}).get("is_valid", False)
        icon = "+" if valid else "!"
        vendor = f.get("vendor", {}).get("name", "?")
        gross = f.get("totals", {}).get("gross_total", 0)
        inv_num = f.get("header", {}).get("invoice_number", "?")
        print(f"  [{icon}] {f.get('filename')}")
        print(f"      Szallito: {vendor} | Szamlaszam: {inv_num} | Brutto: {gross:,.0f} Ft")
        errors = f.get("validation", {}).get("errors", [])
        if errors:
            for e in errors:
                print(f"      HIBA: {e}")

    exported = result.get("exported_files", [])
    if exported:
        print(f"\n  Export:")
        for ep in exported:
            print(f"    -> {ep}")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Invoice Processor - szamla feldolgozo"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Process invoices from source")
    p_ingest.add_argument("--source", "-s", required=True, help="PDF file or directory")
    p_ingest.add_argument("--direction", "-d", default="auto",
                          choices=["incoming", "outgoing", "auto"],
                          help="Invoice direction (default: auto-detect)")
    p_ingest.add_argument("--output", "-o", default="./test_output/invoices",
                          help="Output directory for exports")
    p_ingest.add_argument("--format", "-f", default="all",
                          choices=["csv", "excel", "json", "all"],
                          help="Export format (default: all)")
    p_ingest.add_argument("--no-store", action="store_true",
                          help="Skip database storage")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(cmd_ingest(args))
    else:
        parser.print_help()
