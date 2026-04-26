"""Invoice Finder CLI — mailbox scan → acquire → classify → extract → report."""

import argparse
import asyncio


async def cmd_scan(args: argparse.Namespace) -> None:
    """Scan mailbox for invoices and process them."""
    # Pipeline will be triggered via API, but CLI provides manual scan
    print(f"Scanning mailbox: connector={args.connector}, days={args.days}, limit={args.limit}")
    print(f"Output directory: {args.output}")
    print(
        "Use POST /api/v1/pipelines/{{id}}/run with invoice_finder_v3 pipeline for full execution."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Invoice Finder - szamla kereso es feldolgozo")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_scan = subparsers.add_parser("scan", help="Scan mailbox for invoices")
    p_scan.add_argument("--connector", "-c", required=True, help="Email connector config ID")
    p_scan.add_argument("--days", "-d", type=int, default=30, help="Scan last N days (default: 30)")
    p_scan.add_argument(
        "--limit", "-l", type=int, default=50, help="Max emails to scan (default: 50)"
    )
    p_scan.add_argument(
        "--output", "-o", default="./data/invoices", help="Output directory for invoices"
    )
    p_scan.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.8,
        help="Confidence threshold (default: 0.8)",
    )

    args = parser.parse_args()
    if args.command == "scan":
        asyncio.run(cmd_scan(args))
    else:
        parser.print_help()
