"""Email Intent Processor skill - standalone CLI entry point.

Usage:
    python -m skills.email_intent_processor --input email.eml
    python -m skills.email_intent_processor --input "email body text" --subject "Re: Panasz"
    python -m skills.email_intent_processor --input email.eml --output ./results
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main(input_source: str, subject: str, output_dir: str) -> None:
    from aiflow.engine.skill_runner import SkillRunner
    from skills.email_intent_processor.workflows.classify import (
        parse_email,
        process_attachments,
        classify_intent,
        extract_entities,
        score_priority,
        decide_routing,
        log_result,
    )

    runner = SkillRunner.from_env(
        default_model="openai/gpt-4o-mini",
        prompt_dirs=[Path(__file__).parent / "prompts"],
    )

    print("=" * 60)
    print("Email Intent Processor Skill")
    print("=" * 60)

    # Determine input type: .eml file or raw text
    input_path = Path(input_source)
    if input_path.exists() and input_path.suffix in (".eml", ".msg"):
        print(f"Input: {input_path}")
        initial_data = {"raw_eml_path": str(input_path)}
    else:
        print(f"Input: text ({len(input_source)} chars)")
        if subject:
            print(f"Subject: {subject}")
        initial_data = {
            "body": input_source,
            "subject": subject,
        }

    print()

    result = await runner.run_steps(
        [
            parse_email,
            process_attachments,
            classify_intent,
            extract_entities,
            score_priority,
            decide_routing,
            log_result,
        ],
        initial_data,
    )

    # Display results
    print("-" * 60)
    print("RESULTS")
    print("-" * 60)

    intent = result.get("intent", {})
    priority = result.get("priority", {})
    routing = result.get("routing", {})
    entities = result.get("entities", {})

    print(f"  Intent:     {intent.get('intent_id', '?')} "
          f"({intent.get('intent_display_name', '')}) "
          f"[{intent.get('confidence', 0):.0%}]")
    print(f"  Method:     {intent.get('method', '?')}")
    print(f"  Priority:   {priority.get('priority_name', '?')} "
          f"(level {priority.get('priority_level', '?')}) "
          f"SLA: {priority.get('sla_hours', '?')}h")
    print(f"  Routing:    {routing.get('department_name', '?')} "
          f"-> {routing.get('queue_id', '?')}")

    entity_list = entities.get("entities", [])
    if entity_list:
        print(f"  Entities:   {len(entity_list)} found")
        for ent in entity_list[:5]:
            print(f"    - {ent.get('entity_type', '?')}: {ent.get('value', '?')}")

    if routing.get("escalation_triggered"):
        print(f"  ESCALATION: {routing.get('escalation_reason', '')}")

    # Save JSON output
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        result_file = out_path / "result.json"
        result_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\n  Saved: {result_file}")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Email Intent Processor - classify and route emails"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to .eml file or raw email body text",
    )
    parser.add_argument(
        "--subject", "-s", default="",
        help="Email subject (when using raw text input)",
    )
    parser.add_argument(
        "--output", "-o", default="",
        help="Output directory for JSON results",
    )
    args = parser.parse_args()
    asyncio.run(main(args.input, args.subject, args.output))
