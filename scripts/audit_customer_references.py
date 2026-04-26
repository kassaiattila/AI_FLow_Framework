"""Sprint W SW-3 (SS-FU-1 / SS-FU-5) — audit ``customer`` references.

Greps the source tree for surviving ``customer`` references on the
``rag_collections`` surface (rag_engine service / rag_collections router /
rag_metrics harness). The Sprint W rename moves every kwarg + SQL column
read on this surface to ``tenant_id``; this audit asserts the migration
is complete.

Out of scope (intentionally excluded):
* ``skill_instances.customer`` (separate domain, different table)
* ``intent_schemas.customer`` (separate domain, different table)
* ``document_extractor`` config ``customer`` (DocumentTypeConfig, different surface)
* String literals containing the word ``customer`` (e.g. comments, log
  events, fixture file names) — only Python identifiers / SQL columns count

Usage::

    .venv/Scripts/python.exe scripts/audit_customer_references.py
    .venv/Scripts/python.exe scripts/audit_customer_references.py --strict

Exit code is 0 when zero offending references remain on the targeted
surface, 1 otherwise (only with ``--strict``). Output is plain text by
default; pass ``--output json`` (Sprint U S156 helper) for CI consumption.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"

# rag_collections-surface paths in scope
TARGET_DIRS = (
    SRC / "aiflow" / "services" / "rag_engine",
    SRC / "aiflow" / "services" / "rag_metrics",
    SRC / "aiflow" / "api" / "v1",
)

# `customer` as Python identifier / SQL column (NOT inside string literals or comments)
PATTERNS = (
    re.compile(r"\bcustomer\s*[:=]"),  # `customer:` annotation, `customer =` assignment
    re.compile(r"\bcustomer\s*,"),  # SQL column list / function arg list
    re.compile(r"['\"]customer['\"]"),  # dict key / SQL placeholder
)

# router files outside rag_engine / rag_metrics scope
ROUTER_FILES_IN_SCOPE = ("rag_collections.py", "rag_engine.py", "rag_advanced.py")


def _in_scope(py: Path) -> bool:
    """Return True if file path is within the rag_collections surface."""
    for d in TARGET_DIRS[:2]:  # rag_engine + rag_metrics dirs
        if d in py.parents:
            return True
    if py.parent == TARGET_DIRS[2]:
        return py.name in ROUTER_FILES_IN_SCOPE
    return False


def _scan() -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for py in SRC.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        if not _in_scope(py):
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pat in PATTERNS:
                if pat.search(line):
                    hits.append((py, i, stripped))
                    break
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit `customer` references on the rag_collections surface (SW-3)."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on ANY remaining reference.",
    )

    sys.path.insert(0, str(REPO_ROOT))
    from scripts._common import argparse_output, write_output

    argparse_output(parser, default_mode="text")
    args = parser.parse_args(argv)

    hits = _scan()

    if args.output == "text":
        lines = [f"=== `customer` references on rag_collections surface ({len(hits)}) ==="]
        for path, lineno, snippet in hits:
            lines.append(f"  {path.relative_to(REPO_ROOT)}:{lineno}: {snippet}")
        lines.append("")
        if args.strict and hits:
            lines.append(f"[strict] {len(hits)} reference(s) — Sprint W SW-3 rename incomplete.")
        elif args.strict:
            lines.append("[strict] Zero references — Sprint W SW-3 rename complete.")
        else:
            lines.append("[non-strict] Run with --strict to fail CI on remaining references.")
        write_output(args.output, args.output_path, "\n".join(lines))
    else:
        payload = {
            "strict": args.strict,
            "hits": [
                {"path": str(p.relative_to(REPO_ROOT)), "lineno": ln, "snippet": s}
                for p, ln, s in hits
            ],
            "count": len(hits),
            "ok": not (args.strict and hits),
        }
        write_output(args.output, args.output_path, payload)

    if args.strict and hits:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
