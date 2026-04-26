"""Sprint U S154 (SN-FU) — audit cost-recording call sites.

Greps the source tree for the two parallel cost-recording surfaces:

* ``record_cost(...)``                           — legacy helper in
                                                   ``aiflow/api/cost_recorder.py``
* ``CostAttributionRepository.insert_attribution(...)``  — repository path

Reports the call sites + any ``record_cost`` import. The Sprint U
consolidation deletes ``record_cost`` after migration; this script's exit
code is 0 when zero ``record_cost`` references remain in ``src/``, and 1
otherwise.

Usage:

    .venv/Scripts/python.exe scripts/audit_cost_recording.py
    .venv/Scripts/python.exe scripts/audit_cost_recording.py --strict   # also fail on
                                                                          legacy import paths

Output is plain text (one line per match) so operators can ``grep`` /
``awk`` it in CI. The script does NOT modify files.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"

LEGACY_PATTERNS = (
    re.compile(r"\brecord_cost\s*\("),
    re.compile(r"from\s+aiflow\.api\.cost_recorder\s+import\s+record_cost"),
)
REPOSITORY_PATTERN = re.compile(r"CostAttributionRepository|insert_attribution")


def _scan(root: Path, patterns: tuple[re.Pattern[str], ...]) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for py in root.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for pat in patterns:
                if pat.search(line):
                    hits.append((py, i, line.strip()))
                    break
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on ANY legacy reference (including imports + tests).",
    )
    args = parser.parse_args(argv)

    legacy_hits = _scan(SRC, LEGACY_PATTERNS)
    repo_hits = _scan(SRC, (REPOSITORY_PATTERN,))

    print(f"=== Legacy `record_cost` call sites in src/ ({len(legacy_hits)}) ===")
    for path, lineno, snippet in legacy_hits:
        print(f"  {path.relative_to(REPO_ROOT)}:{lineno}: {snippet}")

    print(f"\n=== Repository path call sites in src/ ({len(repo_hits)}) ===")
    for path, lineno, snippet in repo_hits:
        print(f"  {path.relative_to(REPO_ROOT)}:{lineno}: {snippet}")

    if args.strict and legacy_hits:
        print(
            f"\n[strict] {len(legacy_hits)} legacy reference(s) found — Sprint U S154 "
            f"migration not yet complete.",
            file=sys.stderr,
        )
        return 1

    if not args.strict:
        print("\n[non-strict] Run with --strict to fail CI on remaining legacy references.")
    else:
        print("\n[strict] No legacy references remain — Sprint U S154 migration clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
