"""Scope guardrail — 3-tier boundary enforcement for skill inputs.

Classification tiers:
    1. **IN_SCOPE** — topic matches allowed list; proceed normally.
    2. **OUT_OF_SCOPE** — topic is outside skill scope; polite refusal.
    3. **DANGEROUS** — topic matches dangerous patterns; hard block + alert.
"""

from __future__ import annotations

import re

import structlog

from aiflow.guardrails.base import (
    GuardrailBase,
    GuardrailResult,
    GuardrailViolation,
    ScopeVerdict,
    Severity,
)

__all__ = ["ScopeGuard"]

logger = structlog.get_logger(__name__)


class ScopeGuard(GuardrailBase):
    """3-tier scope boundary enforcement.

    Args:
        allowed_topics: Keywords/phrases that define the skill's domain.
        blocked_topics: Topics the skill must refuse (polite out-of-scope).
        dangerous_patterns: Regex patterns that trigger hard block.
    """

    def __init__(
        self,
        *,
        allowed_topics: list[str] | None = None,
        blocked_topics: list[str] | None = None,
        dangerous_patterns: list[str] | None = None,
    ) -> None:
        self._allowed_topics = [t.lower() for t in (allowed_topics or [])]
        self._blocked_topics = [t.lower() for t in (blocked_topics or [])]
        self._dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in (dangerous_patterns or [])
        ]

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        """Classify text as in-scope, out-of-scope, or dangerous."""
        text_lower = text.lower()

        # Priority 1: Dangerous patterns — CRITICAL block
        for pattern in self._dangerous_patterns:
            if pattern.search(text_lower):
                logger.warning(
                    "scope_guard_dangerous",
                    pattern=pattern.pattern,
                    text_preview=text[:100],
                )
                return GuardrailResult(
                    passed=False,
                    violations=[
                        GuardrailViolation(
                            rule="dangerous_content",
                            message="Request contains dangerous content — blocked",
                            severity=Severity.CRITICAL,
                            details={"matched_pattern": pattern.pattern},
                        )
                    ],
                    scope_verdict=ScopeVerdict.DANGEROUS,
                )

        # Priority 2: Blocked topics — WARNING refusal
        for topic in self._blocked_topics:
            if topic in text_lower:
                logger.info("scope_guard_out_of_scope", blocked_topic=topic)
                return GuardrailResult(
                    passed=False,
                    violations=[
                        GuardrailViolation(
                            rule="out_of_scope",
                            message=f"Topic '{topic}' is outside this skill's scope",
                            severity=Severity.WARNING,
                            details={"blocked_topic": topic},
                        )
                    ],
                    scope_verdict=ScopeVerdict.OUT_OF_SCOPE,
                )

        # Priority 3: Check if any allowed topic matches
        if self._allowed_topics:
            matched = [t for t in self._allowed_topics if t in text_lower]
            if matched:
                return GuardrailResult(
                    passed=True,
                    scope_verdict=ScopeVerdict.IN_SCOPE,
                    metadata={"matched_topics": matched},
                )

            # No allowed topic matched — out of scope
            return GuardrailResult(
                passed=False,
                violations=[
                    GuardrailViolation(
                        rule="out_of_scope",
                        message="No allowed topic matched — request is out of scope",
                        severity=Severity.WARNING,
                        details={"allowed_topics": self._allowed_topics},
                    )
                ],
                scope_verdict=ScopeVerdict.OUT_OF_SCOPE,
            )

        # No allowed_topics configured — everything is in-scope by default
        return GuardrailResult(
            passed=True,
            scope_verdict=ScopeVerdict.IN_SCOPE,
        )
