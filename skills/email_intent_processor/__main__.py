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
    from skills.email_intent_processor.workflows.classify import (
        classify_intent,
        decide_routing,
        extract_entities,
        log_result,
        parse_email,
        process_attachments,
        score_priority,
    )

    from aiflow.engine.skill_runner import SkillRunner

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


async def cmd_discover(args: argparse.Namespace) -> None:
    """Discover intent categories from real emails."""
    import json as _json

    from skills.email_intent_processor.discovery.intent_discoverer import discover_intents

    print("=" * 60)
    print("Intent Discovery - analyzing real emails")
    print("=" * 60)

    result = await discover_intents(
        email_dir=Path(args.emails),
        output_path=Path(args.output) if args.output else None,
        batch_size=args.batch_size,
    )

    print(f"\nAnalyzed: {result.total_emails} emails")
    print(f"Cost: ${result.total_cost_usd:.4f}")
    print(f"\nDiscovered {len(result.discovered_intents)} intent categories:")
    for intent in result.discovered_intents:
        freq = f"{intent.estimated_frequency:.0%}" if intent.estimated_frequency else f"{intent.email_count}x"
        print(f"  - {intent.id}: {intent.display_name} ({freq})")
        if intent.keywords_hu:
            print(f"    Keywords: {', '.join(intent.keywords_hu[:5])}")

    print("\nSchema comparison:")
    for comp in result.schema_comparison:
        icon = {"validated": "+", "missing_from_data": "-", "new_in_data": "*"}.get(comp.status, "?")
        name = comp.schema_intent_id or comp.discovered_match
        print(f"  [{icon}] {name} — {comp.status} {comp.notes}")

    # Save customer-specific schema if --customer specified
    if args.customer:
        schema_dir = Path("deployments") / args.customer / "schemas" / "email_intent_processor"
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_path = schema_dir / "intents.json"
        customer_schema = {
            "schema_version": "v1",
            "customer": args.customer,
            "source": "intent_discovery",
            "discovery_date": result.email_assignments[0].email_id if result.email_assignments else "",
            "total_emails_analyzed": result.total_emails,
            "discovery_cost_usd": result.total_cost_usd,
            "intents": [
                {
                    "id": d.id,
                    "display_name": d.display_name,
                    "display_name_en": d.display_name_en,
                    "description": d.description,
                    "keywords_hu": d.keywords_hu,
                    "keywords_en": d.keywords_en,
                    "examples": d.example_subjects,
                    "routing": {"queue": f"q_{d.id}", "priority_boost": 0, "sla_hours": 48},
                    "ml_label": d.id,
                    "sub_intents": [],
                }
                for d in result.discovered_intents
            ],
        }
        schema_path.write_text(
            _json.dumps(customer_schema, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nCustomer schema saved: {schema_path}")

    if args.output:
        print(f"Full results saved to: {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Email Intent Processor - classify, discover, and train"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # classify (default behavior, backward compatible)
    p_classify = subparsers.add_parser("classify", help="Classify a single email")
    p_classify.add_argument("--input", "-i", required=True, help="Path to .eml or raw text")
    p_classify.add_argument("--subject", "-s", default="", help="Email subject")
    p_classify.add_argument("--output", "-o", default="", help="Output directory")

    # discover
    p_discover = subparsers.add_parser("discover", help="Discover intents from real emails")
    p_discover.add_argument("--emails", "-e", required=True, help="Directory with .eml files")
    p_discover.add_argument("--customer", "-c", default="", help="Customer name (saves schema to deployments/{customer}/)")
    p_discover.add_argument("--output", "-o", default="", help="Output JSON path for full results")
    p_discover.add_argument("--batch-size", type=int, default=8, help="Emails per LLM batch")

    args = parser.parse_args()

    if args.command == "discover":
        asyncio.run(cmd_discover(args))
    elif args.command == "classify" or not args.command:
        # Backward compatible: no subcommand = classify
        if not args.command:
            parser.add_argument("--input", "-i", required=True)
            parser.add_argument("--subject", "-s", default="")
            parser.add_argument("--output", "-o", default="")
            args = parser.parse_args()
        asyncio.run(main(args.input, args.subject, args.output))
    else:
        parser.print_help()
