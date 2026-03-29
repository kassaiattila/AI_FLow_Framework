"""LLM-based intent classifier - uses ModelClient + PromptManager.

Classifies email text using an LLM with the intent schema (intents.json)
as context. The LLM sees all available intent categories, their descriptions,
and examples from the schema, enabling zero-shot and few-shot classification.
"""
from __future__ import annotations

from typing import Any

import structlog

from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager
from skills.email_intent_processor.models import IntentResult

__all__ = ["LLMClassifier"]

logger = structlog.get_logger(__name__)


class _LLMClassifyOutput:
    """Expected LLM output structure (parsed from JSON)."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.intent_id: str = data.get("intent_id", "unknown")
        self.confidence: float = float(data.get("confidence", 0.5))
        self.sub_intent: str = data.get("sub_intent", "")
        self.reasoning: str = data.get("reasoning", "")
        self.alternatives: list[dict] = data.get("alternatives", [])


class LLMClassifier:
    """LLM-based intent classifier using prompts and schema definitions.

    Uses the intent_classifier prompt from prompts/ and the intents
    schema to provide the LLM with available categories.
    """

    def __init__(
        self,
        models_client: ModelClient,
        prompt_manager: PromptManager,
        prompt_name: str = "email-intent/classifier",
    ) -> None:
        self.models_client = models_client
        self.prompt_manager = prompt_manager
        self.prompt_name = prompt_name

    async def classify(
        self,
        text: str,
        subject: str = "",
        schema_intents: list[dict] | None = None,
    ) -> IntentResult:
        """Classify email text into one of the defined intents.

        Args:
            text: Email body text.
            subject: Email subject line.
            schema_intents: List of intent definitions from intents.json.
        """
        # Build intent catalog for the prompt
        intent_catalog = self._build_intent_catalog(schema_intents or [])

        prompt = self.prompt_manager.get(self.prompt_name)
        messages = prompt.compile(
            variables={
                "subject": subject,
                "body": text[:3000],  # Truncate very long emails
                "intent_catalog": intent_catalog,
            }
        )

        try:
            result = await self.models_client.generate(
                messages=messages,
                model=prompt.config.model,
                temperature=prompt.config.temperature,
                max_tokens=prompt.config.max_tokens,
            )

            parsed = self._parse_response(result.output.text)

            # Look up display name from schema
            display_name = ""
            if schema_intents:
                for intent_def in schema_intents:
                    if intent_def.get("id") == parsed.intent_id:
                        display_name = intent_def.get("display_name", "")
                        break

            intent_result = IntentResult(
                intent_id=parsed.intent_id,
                intent_display_name=display_name,
                confidence=round(parsed.confidence, 4),
                sub_intent=parsed.sub_intent,
                method="llm",
                llm_intent=parsed.intent_id,
                llm_confidence=round(parsed.confidence, 4),
                alternatives=parsed.alternatives,
                reasoning=parsed.reasoning,
            )

            logger.info(
                "llm_classify_done",
                intent=intent_result.intent_id,
                confidence=intent_result.confidence,
            )
            return intent_result

        except Exception as e:
            logger.error("llm_classify_failed", error=str(e))
            return IntentResult(
                intent_id="unknown",
                confidence=0.0,
                method="llm_error",
                reasoning=f"LLM classification failed: {e}",
            )

    def _build_intent_catalog(self, schema_intents: list[dict]) -> str:
        """Build a text catalog of intents for the LLM prompt."""
        if not schema_intents:
            return (
                "Available intents: complaint, inquiry, order, support, "
                "feedback, claim, cancellation"
            )

        lines = []
        for intent in schema_intents:
            intent_id = intent.get("id", "")
            display = intent.get("display_name", "")
            desc = intent.get("description", "")
            examples = intent.get("examples", [])
            sub_intents = intent.get("sub_intents", [])

            line = f"- {intent_id} ({display}): {desc}"
            if examples:
                line += f"\n  Examples: {'; '.join(examples[:2])}"
            if sub_intents:
                line += f"\n  Sub-intents: {', '.join(sub_intents)}"
            lines.append(line)

        return "\n".join(lines)

    def _parse_response(self, text: str) -> _LLMClassifyOutput:
        """Parse the LLM JSON response."""
        import json

        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
            return _LLMClassifyOutput(data)
        except json.JSONDecodeError:
            logger.warning("llm_response_not_json", response=text[:200])
            # Attempt to extract intent from free text
            return _LLMClassifyOutput(
                {"intent_id": "unknown", "confidence": 0.3, "reasoning": text[:200]}
            )
