"""LLM-based guardrails — precise fallback for rule-based guards.

Architecture: Rule-based (A5, fast, $0) → LLM (B1.1, precise, $$).
When rule-based guards are uncertain, these LLM guards provide
a second opinion using prompt YAML definitions + gpt-4o-mini.

Each class inherits GuardrailBase and loads its prompt from
``src/aiflow/guardrails/prompts/*.yaml`` via PromptManager.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from aiflow.guardrails.base import (
    GuardrailBase,
    GuardrailResult,
    GuardrailViolation,
    PIIMatch,
    ScopeVerdict,
    Severity,
)
from aiflow.prompts.manager import PromptManager
from aiflow.prompts.schema import PromptDefinition

__all__ = [
    "LLMHallucinationEvaluator",
    "LLMContentSafetyClassifier",
    "LLMScopeClassifier",
    "LLMPIIDetector",
]

logger = structlog.get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str, prompt_manager: PromptManager | None = None) -> PromptDefinition:
    """Load a guardrail prompt YAML by filename (without extension)."""
    if prompt_manager is not None:
        try:
            return prompt_manager.get(f"guardrails/{name}")
        except KeyError:
            pass
    # Direct YAML fallback
    yaml_path = _PROMPTS_DIR / f"{name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Guardrail prompt not found: {yaml_path}")
    mgr = PromptManager()
    return mgr.load_yaml(yaml_path)


async def _call_llm(
    prompt: PromptDefinition,
    variables: dict[str, Any],
    model: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Call LLM with a compiled prompt and return parsed JSON response."""
    import litellm

    messages = prompt.compile(variables)
    used_model = model or prompt.config.model

    response = await litellm.acompletion(
        model=used_model,
        messages=messages,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
        timeout=timeout,
    )
    text = response.choices[0].message.content or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("llm_guard_json_parse_error", text=text[:200])
        return {}


class LLMHallucinationEvaluator(GuardrailBase):
    """LLM-based grounding evaluator.

    Replaces the A5 SequenceMatcher heuristic with an LLM that analyzes
    whether response claims are grounded in source documents.

    Args:
        threshold: Grounding score below which output is flagged (0-1).
        model: Override model (default from prompt YAML).
        prompt_manager: Optional shared PromptManager instance.
        timeout: LLM call timeout in seconds.
    """

    def __init__(
        self,
        *,
        threshold: float = 0.7,
        model: str | None = None,
        prompt_manager: PromptManager | None = None,
        timeout: int = 15,
    ) -> None:
        self._threshold = threshold
        self._model = model
        self._timeout = timeout
        self._prompt = _load_prompt("hallucination_evaluator", prompt_manager)

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        """Synchronous wrapper — use ``acheck`` for async."""
        raise NotImplementedError("LLMHallucinationEvaluator requires async. Use acheck() instead.")

    async def acheck(self, text: str, **kwargs: object) -> GuardrailResult:
        """Evaluate grounding of a response against sources.

        Keyword Args:
            sources: ``list[str]`` of source documents for grounding check.
        """
        sources = kwargs.get("sources", [])
        if not isinstance(sources, list):
            sources = []

        if not sources or not text.strip():
            return GuardrailResult(passed=True, hallucination_score=1.0)

        result = await _call_llm(
            self._prompt,
            {"response": text, "sources": sources},
            model=self._model,
            timeout=self._timeout,
        )

        score = float(result.get("grounding_score", 0.0))
        ungrounded = result.get("ungrounded_claims", [])
        summary = result.get("summary", "")

        violations: list[GuardrailViolation] = []
        if score < self._threshold:
            violations.append(
                GuardrailViolation(
                    rule="llm_hallucination",
                    message=f"Low grounding score ({score:.2f} < {self._threshold}): {summary}",
                    severity=Severity.WARNING,
                    details={
                        "grounding_score": score,
                        "threshold": self._threshold,
                        "ungrounded_claims": ungrounded,
                    },
                )
            )

        logger.info(
            "llm_hallucination_eval",
            score=score,
            ungrounded_count=len(ungrounded),
            passed=not violations,
        )

        return GuardrailResult(
            passed=not violations,
            violations=violations,
            hallucination_score=score,
            metadata={"ungrounded_claims": ungrounded, "summary": summary},
        )


class LLMContentSafetyClassifier(GuardrailBase):
    """LLM-based content safety classifier.

    Replaces the A5 regex-based safety patterns with an LLM that
    classifies text as SAFE, UNSAFE, or REVIEW_NEEDED.

    Args:
        model: Override model (default from prompt YAML).
        prompt_manager: Optional shared PromptManager instance.
        timeout: LLM call timeout in seconds.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        prompt_manager: PromptManager | None = None,
        timeout: int = 15,
    ) -> None:
        self._model = model
        self._timeout = timeout
        self._prompt = _load_prompt("content_safety_classifier", prompt_manager)

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        raise NotImplementedError(
            "LLMContentSafetyClassifier requires async. Use acheck() instead."
        )

    async def acheck(self, text: str, **kwargs: object) -> GuardrailResult:
        """Classify text content safety.

        Keyword Args:
            context: Optional context string for the classification.
        """
        context = kwargs.get("context", "")
        if not isinstance(context, str):
            context = ""

        result = await _call_llm(
            self._prompt,
            {"text": text, "context": context},
            model=self._model,
            timeout=self._timeout,
        )

        verdict = result.get("verdict", "SAFE").upper()
        category = result.get("category")
        confidence = float(result.get("confidence", 0.0))
        reason = result.get("reason", "")

        violations: list[GuardrailViolation] = []
        if verdict == "UNSAFE":
            violations.append(
                GuardrailViolation(
                    rule="llm_content_safety",
                    message=f"Unsafe content ({category}): {reason}",
                    severity=Severity.CRITICAL,
                    details={
                        "verdict": verdict,
                        "category": category,
                        "confidence": confidence,
                    },
                )
            )
        elif verdict == "REVIEW_NEEDED":
            violations.append(
                GuardrailViolation(
                    rule="llm_content_safety_review",
                    message=f"Content needs review ({category}): {reason}",
                    severity=Severity.WARNING,
                    details={
                        "verdict": verdict,
                        "category": category,
                        "confidence": confidence,
                    },
                )
            )

        passed = verdict == "SAFE"

        logger.info(
            "llm_content_safety",
            verdict=verdict,
            category=category,
            confidence=confidence,
            passed=passed,
        )

        return GuardrailResult(
            passed=passed,
            violations=violations,
            metadata={"verdict": verdict, "category": category, "confidence": confidence},
        )


class LLMScopeClassifier(GuardrailBase):
    """LLM-based 3-tier scope classifier.

    Replaces the A5 keyword-matching scope guard with an LLM that
    considers skill context for nuanced scope decisions.

    Args:
        skill_description: Description of the skill's purpose.
        allowed_topics: List of in-scope topics.
        model: Override model (default from prompt YAML).
        prompt_manager: Optional shared PromptManager instance.
        timeout: LLM call timeout in seconds.
    """

    def __init__(
        self,
        *,
        skill_description: str = "",
        allowed_topics: list[str] | None = None,
        model: str | None = None,
        prompt_manager: PromptManager | None = None,
        timeout: int = 15,
    ) -> None:
        self._skill_description = skill_description
        self._allowed_topics = allowed_topics or []
        self._model = model
        self._timeout = timeout
        self._prompt = _load_prompt("scope_classifier", prompt_manager)

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        raise NotImplementedError("LLMScopeClassifier requires async. Use acheck() instead.")

    async def acheck(self, text: str, **kwargs: object) -> GuardrailResult:
        """Classify whether a query is in-scope for this skill."""
        result = await _call_llm(
            self._prompt,
            {
                "query": text,
                "skill_description": self._skill_description,
                "allowed_topics": self._allowed_topics,
            },
            model=self._model,
            timeout=self._timeout,
        )

        verdict_str = result.get("verdict", "in_scope").lower()
        reason = result.get("reason", "")
        confidence = float(result.get("confidence", 0.0))

        verdict_map = {
            "in_scope": ScopeVerdict.IN_SCOPE,
            "out_of_scope": ScopeVerdict.OUT_OF_SCOPE,
            "dangerous": ScopeVerdict.DANGEROUS,
        }
        scope_verdict = verdict_map.get(verdict_str, ScopeVerdict.OUT_OF_SCOPE)

        violations: list[GuardrailViolation] = []
        if scope_verdict == ScopeVerdict.DANGEROUS:
            violations.append(
                GuardrailViolation(
                    rule="llm_scope_dangerous",
                    message=f"Dangerous request: {reason}",
                    severity=Severity.CRITICAL,
                    details={"verdict": verdict_str, "confidence": confidence},
                )
            )
        elif scope_verdict == ScopeVerdict.OUT_OF_SCOPE:
            violations.append(
                GuardrailViolation(
                    rule="llm_scope_out",
                    message=f"Out of scope: {reason}",
                    severity=Severity.WARNING,
                    details={"verdict": verdict_str, "confidence": confidence},
                )
            )

        passed = scope_verdict == ScopeVerdict.IN_SCOPE

        logger.info(
            "llm_scope_classifier",
            verdict=verdict_str,
            confidence=confidence,
            passed=passed,
        )

        return GuardrailResult(
            passed=passed,
            violations=violations,
            scope_verdict=scope_verdict,
            metadata={"reason": reason, "confidence": confidence},
        )


class LLMPIIDetector(GuardrailBase):
    """LLM-based PII detector for free-form text.

    Catches PII that regex cannot: names in context, implicit addresses,
    employer references. Supports Hungarian and English text.

    Args:
        model: Override model (default from prompt YAML).
        prompt_manager: Optional shared PromptManager instance.
        timeout: LLM call timeout in seconds.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        prompt_manager: PromptManager | None = None,
        timeout: int = 15,
    ) -> None:
        self._model = model
        self._timeout = timeout
        self._prompt = _load_prompt("freetext_pii_detector", prompt_manager)

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        raise NotImplementedError("LLMPIIDetector requires async. Use acheck() instead.")

    async def acheck(self, text: str, **kwargs: object) -> GuardrailResult:
        """Detect PII in free-form text using LLM analysis."""
        if not text.strip():
            return GuardrailResult(passed=True)

        result = await _call_llm(
            self._prompt,
            {"text": text},
            model=self._model,
            timeout=self._timeout,
        )

        pii_found = result.get("pii_found", False)
        pii_items = result.get("pii_items", [])

        pii_matches: list[PIIMatch] = []
        for item in pii_items:
            pii_matches.append(
                PIIMatch(
                    pattern_name=item.get("type", "unknown"),
                    matched_text=item.get("text", ""),
                    start=item.get("start", 0),
                    end=item.get("end", 0),
                )
            )

        violations: list[GuardrailViolation] = []
        if pii_found and pii_matches:
            pii_types = list({m.pattern_name for m in pii_matches})
            violations.append(
                GuardrailViolation(
                    rule="llm_pii_detected",
                    message=f"PII detected by LLM: {', '.join(pii_types)}",
                    severity=Severity.WARNING,
                    details={"pii_types": pii_types, "count": len(pii_matches)},
                )
            )

        passed = not pii_found or not pii_matches

        logger.info(
            "llm_pii_detector",
            pii_found=pii_found,
            pii_count=len(pii_matches),
            passed=passed,
        )

        return GuardrailResult(
            passed=passed,
            violations=violations,
            pii_matches=pii_matches,
        )
