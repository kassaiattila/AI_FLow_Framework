"""Intent discovery - analyze real emails to find natural intent categories.

Two-pass algorithm:
1. Individual classification: LLM classifies each email without predefined categories
2. Consolidation: LLM merges similar labels into a canonical taxonomy
Then compares discovered intents with the existing intents.json schema.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field
from skills.email_intent_processor.discovery.email_loader import (
    DiscoveryEmail,
    load_emails_from_dir,
)

from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager
from aiflow.tools.schema_registry import SchemaRegistry

__all__ = [
    "IntentDiscoverer",
    "DiscoveryResult",
    "DiscoveredIntent",
    "discover_intents",
]

logger = structlog.get_logger(__name__)


class EmailAssignment(BaseModel):
    """Assignment of a single email to a discovered intent."""

    email_id: str
    intent_label: str
    confidence: float = 0.0
    keywords: list[str] = []


class DiscoveredIntent(BaseModel):
    """A consolidated intent category discovered from real data."""

    id: str
    display_name: str = ""
    display_name_en: str = ""
    description: str = ""
    merged_from: list[str] = []
    keywords_hu: list[str] = []
    keywords_en: list[str] = []
    example_subjects: list[str] = []
    estimated_frequency: float = 0.0
    email_count: int = 0


class SchemaComparison(BaseModel):
    """Comparison between discovered and schema-defined intents."""

    schema_intent_id: str
    discovered_match: str = ""
    status: str = ""  # "validated", "missing_from_data", "new_in_data"
    notes: str = ""


class DiscoveryResult(BaseModel):
    """Full discovery output."""

    total_emails: int = 0
    discovered_intents: list[DiscoveredIntent] = []
    email_assignments: list[EmailAssignment] = []
    schema_comparison: list[SchemaComparison] = []
    raw_labels: dict[str, int] = Field(default_factory=dict)
    total_cost_usd: float = 0.0


class IntentDiscoverer:
    """Discover intent categories from real email data using LLM."""

    def __init__(
        self,
        model_client: ModelClient | None = None,
        prompt_manager: PromptManager | None = None,
        batch_size: int = 8,
    ) -> None:
        if model_client is None:
            backend = LiteLLMBackend(default_model="openai/gpt-4o")
            model_client = ModelClient(generation_backend=backend, embedding_backend=backend)
        self.model_client = model_client

        if prompt_manager is None:
            prompt_manager = PromptManager()
            prompt_manager.register_yaml_dir(
                Path(__file__).parent.parent / "prompts"
            )
        self.prompt_manager = prompt_manager
        self.batch_size = batch_size

    async def discover(
        self,
        emails: list[DiscoveryEmail],
        schema_path: str = "email_intent_processor",
    ) -> DiscoveryResult:
        """Run full 2-pass intent discovery on a set of emails.

        Args:
            emails: Parsed emails from email_loader.
            schema_path: Skill name for loading existing intents.json.

        Returns:
            DiscoveryResult with discovered intents, assignments, and schema comparison.
        """
        total_cost = 0.0

        # Pass 1: Individual classification
        logger.info("discovery.pass1_start", email_count=len(emails))
        assignments, raw_labels, cost1 = await self._pass1_classify(emails)
        total_cost += cost1
        logger.info(
            "discovery.pass1_done",
            unique_labels=len(raw_labels),
            cost_usd=round(cost1, 4),
        )

        # Pass 2: Consolidation
        logger.info("discovery.pass2_start", raw_labels=len(raw_labels))
        discovered_intents, cost2 = await self._pass2_consolidate(
            raw_labels, assignments, len(emails)
        )
        total_cost += cost2
        logger.info(
            "discovery.pass2_done",
            consolidated_intents=len(discovered_intents),
            cost_usd=round(cost2, 4),
        )

        # Compare with existing schema
        schema_comparison = self._compare_with_schema(discovered_intents, schema_path)

        return DiscoveryResult(
            total_emails=len(emails),
            discovered_intents=discovered_intents,
            email_assignments=assignments,
            schema_comparison=schema_comparison,
            raw_labels=raw_labels,
            total_cost_usd=round(total_cost, 4),
        )

    async def _pass1_classify(
        self, emails: list[DiscoveryEmail]
    ) -> tuple[list[EmailAssignment], dict[str, int], float]:
        """Pass 1: Classify each email individually without predefined categories."""
        prompt = self.prompt_manager.get("email-intent/intent_discovery")
        assignments: list[EmailAssignment] = []
        label_counts: dict[str, int] = {}
        total_cost = 0.0

        # Process in batches
        for batch_start in range(0, len(emails), self.batch_size):
            batch = emails[batch_start : batch_start + self.batch_size]
            batch_data = [
                {
                    "id": Path(e.file_path).stem,
                    "subject": e.subject,
                    "sender": e.sender,
                    "body": e.body[:1500],
                }
                for e in batch
            ]

            messages = prompt.compile(variables={
                "count": len(batch),
                "emails": batch_data,
            })

            result = await self.model_client.generate(
                messages=messages,
                model=prompt.config.model,
                temperature=prompt.config.temperature,
                max_tokens=prompt.config.max_tokens,
            )
            total_cost += result.cost_usd

            parsed = self._parse_pass1_response(result.output.text, batch_data)
            for item in parsed:
                label = item.get("intent_label", "unknown")
                assignments.append(EmailAssignment(
                    email_id=item.get("email_id", ""),
                    intent_label=label,
                    confidence=float(item.get("confidence", 0.5)),
                    keywords=item.get("keywords", []),
                ))
                label_counts[label] = label_counts.get(label, 0) + 1

        return assignments, label_counts, total_cost

    async def _pass2_consolidate(
        self,
        raw_labels: dict[str, int],
        assignments: list[EmailAssignment],
        total_emails: int,
    ) -> tuple[list[DiscoveredIntent], float]:
        """Pass 2: Consolidate raw labels into canonical taxonomy."""
        prompt = self.prompt_manager.get("email-intent/intent_consolidation")

        # Build label info with sample subjects
        label_info: dict[str, dict[str, Any]] = {}
        for label, count in raw_labels.items():
            sample_ids = [a.email_id for a in assignments if a.intent_label == label][:3]
            sample_kw = []
            for a in assignments:
                if a.intent_label == label:
                    sample_kw.extend(a.keywords[:2])
            label_info[label] = {
                "count": count,
                "description": f"Emails classified as '{label}'",
                "sample_subjects": sample_ids,
                "keywords": list(set(sample_kw))[:5],
            }

        messages = prompt.compile(variables={
            "total_emails": total_emails,
            "discovered_labels": label_info,
        })

        result = await self.model_client.generate(
            messages=messages,
            model=prompt.config.model,
            temperature=prompt.config.temperature,
            max_tokens=prompt.config.max_tokens,
        )

        intents = self._parse_consolidation_response(result.output.text)
        return intents, result.cost_usd

    def _compare_with_schema(
        self,
        discovered: list[DiscoveredIntent],
        schema_path: str,
    ) -> list[SchemaComparison]:
        """Compare discovered intents with existing intents.json schema."""
        comparisons: list[SchemaComparison] = []

        try:
            skills_dir = Path(__file__).parent.parent.parent
            sr = SchemaRegistry(skills_dir=skills_dir)
            schema = sr.load_schema(schema_path, "intents")
            schema_intents = {i["id"]: i for i in schema.get("intents", [])}
        except Exception as exc:
            logger.warning("discovery.schema_load_failed", error=str(exc))
            return comparisons

        discovered_merged = set()
        for d in discovered:
            discovered_merged.update(d.merged_from)

        # Check each schema intent
        for sid, sdef in schema_intents.items():
            match = ""
            status = "missing_from_data"
            for d in discovered:
                if sid == d.id or sid in d.merged_from or sid in d.id:
                    match = d.id
                    status = "validated"
                    break
            comparisons.append(SchemaComparison(
                schema_intent_id=sid,
                discovered_match=match,
                status=status,
                notes=sdef.get("display_name", ""),
            ))

        # Check for new intents not in schema
        for d in discovered:
            if not any(c.discovered_match == d.id for c in comparisons):
                comparisons.append(SchemaComparison(
                    schema_intent_id="",
                    discovered_match=d.id,
                    status="new_in_data",
                    notes=d.display_name,
                ))

        return comparisons

    @staticmethod
    def _parse_pass1_response(
        text: str, batch_data: list[dict]
    ) -> list[dict[str, Any]]:
        """Parse LLM response from Pass 1."""
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            if isinstance(data, dict):
                # Might be wrapped in a key
                for key in ("emails", "results", "classifications"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IndexError):
            logger.warning("discovery.parse_error", text_preview=text[:200])
            # Fallback: assign "unknown" to all emails in batch
            return [
                {"email_id": d["id"], "intent_label": "unknown", "confidence": 0.0}
                for d in batch_data
            ]

    @staticmethod
    def _parse_consolidation_response(text: str) -> list[DiscoveredIntent]:
        """Parse LLM response from Pass 2 consolidation."""
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            raw_intents = data.get("intents", data if isinstance(data, list) else [])
            return [
                DiscoveredIntent(
                    id=item.get("id", "unknown"),
                    display_name=item.get("display_name", ""),
                    display_name_en=item.get("display_name_en", ""),
                    description=item.get("description", ""),
                    merged_from=item.get("merged_from", []),
                    keywords_hu=item.get("keywords_hu", []),
                    keywords_en=item.get("keywords_en", []),
                    example_subjects=item.get("example_subjects", []),
                    estimated_frequency=float(item.get("estimated_frequency", 0)),
                    email_count=int(item.get("email_count", 0)),
                )
                for item in raw_intents
            ]
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("discovery.consolidation_parse_error", error=str(exc))
            return []


async def discover_intents(
    email_dir: Path,
    output_path: Path | None = None,
    batch_size: int = 8,
) -> DiscoveryResult:
    """Convenience function: discover intents from an email directory.

    Args:
        email_dir: Directory with .eml files.
        output_path: Optional path to save results as JSON.
        batch_size: Emails per LLM batch call.

    Returns:
        DiscoveryResult with discovered intents.
    """
    emails = load_emails_from_dir(email_dir)
    discoverer = IntentDiscoverer(batch_size=batch_size)
    result = await discoverer.discover(emails)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        logger.info("discovery.saved", path=str(output_path))

    return result
