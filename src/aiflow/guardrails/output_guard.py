"""Output guardrail — validates LLM responses before they reach the user.

Checks for PII leakage, content safety, and basic hallucination scoring
(response vs. source overlap).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import structlog

from aiflow.guardrails.base import (
    GuardrailBase,
    GuardrailResult,
    GuardrailViolation,
    PIIMatch,
    Severity,
)
from aiflow.guardrails.input_guard import PII_PATTERNS

__all__ = ["OutputGuard"]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Content safety patterns (output-specific)
# ---------------------------------------------------------------------------
UNSAFE_CONTENT_PATTERNS: list[tuple[str, str, Severity]] = [
    (
        r"\b(kill|murder|assassinate)\s+(yourself|someone|people)\b",
        "violence_incitement",
        Severity.CRITICAL,
    ),
    (
        r"\b(how\s+to\s+make\s+a?\s*bomb|build\s+a?\s*weapon)\b",
        "weapon_instructions",
        Severity.CRITICAL,
    ),
    (r"\b(hack\s+into|break\s+into\s+a?\s*system)\b", "hacking_instructions", Severity.WARNING),
    (r"<script[\s>]", "xss_in_output", Severity.CRITICAL),
]


class OutputGuard(GuardrailBase):
    """Validates LLM output before delivering to the user.

    Args:
        check_pii: Whether to detect PII leakage.
        check_safety: Whether to run content safety patterns.
        hallucination_threshold: Score above which output is considered grounded (0-1).
            Hallucination check only runs when ``sources`` kwarg is provided.
    """

    def __init__(
        self,
        *,
        check_pii: bool = True,
        check_safety: bool = True,
        hallucination_threshold: float = 0.3,
    ) -> None:
        self._check_pii = check_pii
        self._check_safety = check_safety
        self._hallucination_threshold = hallucination_threshold

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        """Run all output guardrail checks.

        Keyword Args:
            sources: Optional ``list[str]`` of source texts for hallucination scoring.
        """
        violations: list[GuardrailViolation] = []
        pii_matches: list[PIIMatch] = []
        hallucination_score: float | None = None

        # 1. PII leak
        if self._check_pii:
            found = self._detect_pii(text)
            pii_matches.extend(found)
            if found:
                violations.append(
                    GuardrailViolation(
                        rule="pii_in_output",
                        message=f"PII leaked in output: {', '.join(m.pattern_name for m in found)}",
                        severity=Severity.WARNING,
                        details={"pii_types": [m.pattern_name for m in found]},
                    )
                )

        # 2. Content safety
        if self._check_safety:
            violations.extend(self._check_content_safety(text))

        # 3. Hallucination scoring (only when sources provided)
        sources = kwargs.get("sources")
        if sources is not None and isinstance(sources, list):
            hallucination_score = self._hallucination_score(text, sources)
            if hallucination_score < self._hallucination_threshold:
                violations.append(
                    GuardrailViolation(
                        rule="hallucination_risk",
                        message=(
                            f"Low grounding score ({hallucination_score:.2f} "
                            f"< {self._hallucination_threshold})"
                        ),
                        severity=Severity.WARNING,
                        details={
                            "grounding_score": hallucination_score,
                            "threshold": self._hallucination_threshold,
                        },
                    )
                )

        passed = not violations

        if not passed:
            logger.warning(
                "output_guard_violation",
                violation_count=len(violations),
                rules=[v.rule for v in violations],
            )

        return GuardrailResult(
            passed=passed,
            violations=violations,
            pii_matches=pii_matches,
            hallucination_score=hallucination_score,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_pii(text: str) -> list[PIIMatch]:
        matches: list[PIIMatch] = []
        for compiled, name in PII_PATTERNS:
            for m in compiled.finditer(text):
                matches.append(
                    PIIMatch(
                        pattern_name=name,
                        matched_text=m.group(),
                        start=m.start(),
                        end=m.end(),
                    )
                )
        return matches

    @staticmethod
    def _check_content_safety(text: str) -> list[GuardrailViolation]:
        violations: list[GuardrailViolation] = []
        for pattern, label, severity in UNSAFE_CONTENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    GuardrailViolation(
                        rule="content_safety",
                        message=f"Unsafe content detected: {label}",
                        severity=severity,
                        details={"pattern_label": label},
                    )
                )
        return violations

    @staticmethod
    def _hallucination_score(response: str, sources: list[str]) -> float:
        """Compute a simple grounding score (0-1) based on text overlap.

        Uses sentence-level longest-common-subsequence ratio between the
        response and source texts.  Higher = better grounded.

        This is a heuristic baseline; production systems should use an
        LLM-based grounding evaluator (e.g. Promptfoo ``factuality``).
        """
        if not sources or not response.strip():
            return 0.0

        combined_source = " ".join(sources)
        # Split response into sentences for granular scoring
        sentences = re.split(r"[.!?]\s+", response.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return 1.0  # Very short response — cannot assess

        scores: list[float] = []
        for sentence in sentences:
            ratio = SequenceMatcher(None, sentence.lower(), combined_source.lower()).ratio()
            scores.append(ratio)

        return sum(scores) / len(scores)
