"""Process Documentation skill - standalone entry point.

Usage:
    python -m skills.process_documentation --input "Szabadsag igenyeles folyamata..."
    python -m skills.process_documentation --input "Szamla feldolgozas..." --output ./output
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main(input_text: str, output_dir: str) -> None:
    from aiflow.engine.skill_runner import SkillRunner
    from skills.process_documentation.workflow import (
        classify_intent, elaborate, extract, review,
        generate_diagram, export_all,
    )

    runner = SkillRunner.from_env(
        default_model="openai/gpt-4o-mini",
        prompt_dirs=[Path(__file__).parent / "prompts"],
    )

    print(f"Process Documentation Skill")
    print(f"Input: {input_text[:80]}...")
    print(f"Output: {output_dir}")
    print()

    result = await runner.run_steps(
        [classify_intent, elaborate, extract, review, generate_diagram, export_all],
        {"user_input": input_text, "output_dir": output_dir},
    )

    if result.get("rejected"):
        print(f"Elutasitva: {result.get('reason')}")
        return

    print(f"Kész!")
    print(f"Folyamat: {result.get('title', '?')}")
    for f in result.get("saved_files", []):
        print(f"  -> {f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Documentation - diagram generation")
    parser.add_argument("--input", "-i", required=True, help="Process description (Hungarian or English)")
    parser.add_argument("--output", "-o", default="./output/diagrams", help="Output directory")
    args = parser.parse_args()
    asyncio.run(main(args.input, args.output))
