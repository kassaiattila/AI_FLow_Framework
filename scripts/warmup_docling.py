"""Pre-load the docling converter before first real use (Sprint O FU-4).

Measured cold-start on the S127 fixture corpus was p95 17.5 s + first-parse
~60 s model-load. Running this script once before `make api` (or as a CI
step, or as a `docker compose` init container) warms the cache so the
first real parse in production lands in the hot path.

Usage::

    .venv/Scripts/python.exe scripts/warmup_docling.py

Exit codes:
    0 — warmup completed cleanly (or optional deps missing, see --strict)
    2 — warmup failed and --strict was set (blocks boot)

Typical output::

    [warmup] elapsed=73.2s warmed=True
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from aiflow.ingestion.parsers.docling_parser import DoclingParser  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when warmup fails (reportlab/docling missing, etc.).",
    )
    args = parser.parse_args(argv)

    dp = DoclingParser()
    result = dp.warmup()

    print(
        f"[warmup] elapsed={result.elapsed_seconds:.1f}s "
        f"warmed={result.warmed}" + (f" reason={result.reason!r}" if result.reason else "")
    )

    if not result.warmed and args.strict:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
