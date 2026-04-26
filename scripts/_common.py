"""Sprint U S156 (ST-FU-4) — shared operator script helpers.

Provides a uniform ``--output {text|json|jsonl}`` flag + writer so the operator
measurement scripts (``measure_uc1_golden_path``, ``run_nightly_rag_metrics``,
``measure_uc3_*``, ``bootstrap_bge_m3``, ``audit_cost_recording``) emit
consistently shaped output.

Usage::

    from scripts._common import argparse_output, write_output

    parser = argparse.ArgumentParser(...)
    argparse_output(parser, default_mode="text")  # adds --output + --output-path
    args = parser.parse_args()

    payload = {...}                                # dict / list / str
    write_output(args.output, args.output_path, payload)

The helper is import-safe even when ``scripts/`` is not on ``sys.path`` —
operators can also use it directly: ``python -m scripts._common --help``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "OutputMode",
    "argparse_output",
    "write_output",
]

OutputMode = Literal["text", "json", "jsonl"]
_VALID_MODES: tuple[OutputMode, ...] = ("text", "json", "jsonl")


def argparse_output(
    parser: argparse.ArgumentParser,
    *,
    default_mode: OutputMode = "text",
    description: str | None = None,
) -> None:
    """Add ``--output`` and ``--output-path`` flags to an argparse parser.

    Adds two flags:

    * ``--output {text,json,jsonl}`` — output shape. Defaults to ``default_mode``.
    * ``--output-path PATH`` — file path; ``-`` (default) means stdout.

    The script reads ``args.output`` and ``args.output_path`` and passes both
    to :func:`write_output`.
    """
    grp = parser.add_argument_group("output", description or "Output formatting (Sprint U S156)")
    grp.add_argument(
        "--output",
        choices=list(_VALID_MODES),
        default=default_mode,
        help=f"Output shape (default: {default_mode}).",
    )
    grp.add_argument(
        "--output-path",
        default="-",
        help="File path to write to. Default '-' (stdout).",
    )


def _format_payload(mode: OutputMode, payload: Any) -> str:
    if mode == "json":
        return json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False)
    if mode == "jsonl":
        if isinstance(payload, list):
            return "\n".join(
                json.dumps(item, sort_keys=False, ensure_ascii=False) for item in payload
            )
        return json.dumps(payload, sort_keys=False, ensure_ascii=False)
    if mode == "text":
        if isinstance(payload, str):
            return payload
        if isinstance(payload, list):
            return "\n".join(
                str(item) if isinstance(item, (str, int, float, bool)) else json.dumps(item)
                for item in payload
            )
        if isinstance(payload, dict):
            return "\n".join(f"{k}: {v}" for k, v in payload.items())
        return str(payload)
    raise ValueError(f"unknown output mode: {mode!r}")


def write_output(
    mode: OutputMode,
    path: str,
    payload: Any,
) -> None:
    """Write ``payload`` to ``path`` in the requested ``mode``.

    * ``path == "-"`` writes to stdout (no trailing newline beyond the payload).
    * Otherwise writes the file (``utf-8``, parents auto-created).

    The function does not raise on a single payload-shape mismatch — text mode
    accepts ``str | list | dict | scalar`` and falls back to ``str(payload)``.
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"unknown output mode: {mode!r}")

    rendered = _format_payload(mode, payload)

    if path == "-":
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
        return

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = "\n" if not rendered.endswith("\n") else ""
    out_path.write_text(rendered + suffix, encoding="utf-8")
