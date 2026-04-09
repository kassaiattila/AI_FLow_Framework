"""Spec Writer skill — standalone CLI entry point.

Usage:
    python -m skills.spec_writer --input "Leiras..." --type feature --language hu
    python -m skills.spec_writer --input-file spec_request.txt --type api -o spec.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def _run(
    raw_text: str,
    spec_type: str,
    language: str,
    context: str | None,
    output: Path | None,
) -> int:
    from skills.spec_writer.models import SpecInput
    from skills.spec_writer.workflows.spec_writing import run_spec_writing

    inp = SpecInput(
        raw_text=raw_text,
        spec_type=spec_type,  # type: ignore[arg-type]
        language=language,  # type: ignore[arg-type]
        context=context,
    )

    print(f"Spec Writer ({spec_type} / {language})")
    print(f"Input length: {len(raw_text)} chars")
    print()

    result = await run_spec_writing(inp)

    print(f"Title:  {result.draft.title}")
    print(f"Score:  {result.review.score:.1f}/10")
    print(f"Accept: {'YES' if result.review.is_acceptable else 'NO'}")
    if result.review.missing_sections:
        print(f"Missing: {', '.join(result.review.missing_sections)}")
    print()

    if output:
        output.write_text(result.final_markdown, encoding="utf-8")
        json_path = output.with_suffix(".json")
        json_path.write_text(
            json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote: {output}")
        print(f"Wrote: {json_path}")
    else:
        print("--- SPEC MARKDOWN ---")
        print(result.final_markdown)

    return 0 if result.review.is_acceptable else 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spec Writer CLI")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", "-i", help="Raw spec description")
    src.add_argument("--input-file", "-f", type=Path, help="Read raw spec description from a file")
    parser.add_argument(
        "--type",
        "-t",
        default="feature",
        choices=["feature", "api", "db", "user_story"],
    )
    parser.add_argument("--language", "-l", default="hu", choices=["hu", "en"])
    parser.add_argument("--context", "-c", default=None, help="Optional context")
    parser.add_argument(
        "--output", "-o", type=Path, default=None, help="Write markdown to this path"
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    raw_text = args.input_file.read_text(encoding="utf-8") if args.input_file else args.input

    rc = asyncio.run(
        _run(
            raw_text=raw_text,
            spec_type=args.type,
            language=args.language,
            context=args.context,
            output=args.output,
        )
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
