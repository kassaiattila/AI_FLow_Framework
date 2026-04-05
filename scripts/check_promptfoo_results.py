#!/usr/bin/env python3
"""Check Promptfoo evaluation results and enforce minimum pass rate.

Usage:
    python scripts/check_promptfoo_results.py results.json --min-pass-rate 0.9

Exit codes:
    0 - Pass rate meets or exceeds threshold
    1 - Pass rate below threshold or file not found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Promptfoo evaluation results"
    )
    parser.add_argument(
        "results_file",
        type=str,
        help="Path to Promptfoo results JSON file",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.9,
        help="Minimum pass rate (0.0 to 1.0, default: 0.9)",
    )
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"ERROR: Results file not found: {results_path}")
        return 1

    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Failed to read results file: {exc}")
        return 1

    # Promptfoo results structure: {results: [{success: bool, ...}, ...]}
    results = data.get("results", [])
    if not results:
        print("WARNING: No evaluation results found in file.")
        # Empty results count as pass (no prompts to test)
        return 0

    total = len(results)
    passed = sum(1 for r in results if r.get("success", False))
    failed = total - passed
    pass_rate = passed / total if total > 0 else 0.0

    print(f"Promptfoo Results Summary:")
    print(f"  Total:     {total}")
    print(f"  Passed:    {passed}")
    print(f"  Failed:    {failed}")
    print(f"  Pass rate: {pass_rate:.1%}")
    print(f"  Threshold: {args.min_pass_rate:.1%}")
    print()

    if pass_rate < args.min_pass_rate:
        print(
            f"FAIL: Pass rate {pass_rate:.1%} is below "
            f"threshold {args.min_pass_rate:.1%}"
        )
        # Print failed test details
        for r in results:
            if not r.get("success", False):
                prompt = r.get("prompt", {})
                label = prompt.get("label", "unknown")
                error = r.get("error", "no details")
                print(f"  FAILED: {label} — {error}")
        return 1

    print(
        f"PASS: Pass rate {pass_rate:.1%} meets "
        f"threshold {args.min_pass_rate:.1%}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
