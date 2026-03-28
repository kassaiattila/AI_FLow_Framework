"""Input/output guardrails for content safety."""
from __future__ import annotations

import re

import structlog
from pydantic import BaseModel

__all__ = ["GuardrailResult", "InputGuardrail", "OutputGuardrail"]

logger = structlog.get_logger(__name__)

# Common PII patterns
PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # US SSN
    r"\b\d{9}\b",  # 9-digit number (potential SSN without dashes)
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",  # US phone
]

# Forbidden patterns (prompt injection, etc.)
FORBIDDEN_PATTERNS = [
    r"ignore\s+(previous|all)\s+instructions",
    r"system\s*prompt",
    r"<script[\s>]",
    r"javascript:",
]


class GuardrailResult(BaseModel):
    """Result of a guardrail check."""

    passed: bool = True
    violations: list[str] = []
    sanitized_text: str | None = None


class InputGuardrail:
    """Validates and sanitizes user input."""

    def __init__(
        self,
        max_length: int = 10000,
        check_pii: bool = True,
        check_injection: bool = True,
    ) -> None:
        self._max_length = max_length
        self._check_pii = check_pii
        self._check_injection = check_injection

    def check(self, text: str) -> GuardrailResult:
        """Run all input guardrail checks."""
        violations: list[str] = []

        # Length check
        if len(text) > self._max_length:
            violations.append(
                f"Input exceeds maximum length ({len(text)} > {self._max_length})"
            )

        # Forbidden patterns (prompt injection)
        if self._check_injection:
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(f"Forbidden pattern detected: {pattern}")

        # PII detection
        if self._check_pii:
            for pattern in PII_PATTERNS:
                if re.search(pattern, text):
                    violations.append(f"Potential PII detected: {pattern}")

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
        )


class OutputGuardrail:
    """Validates and sanitizes LLM output."""

    def __init__(self, check_pii: bool = True) -> None:
        self._check_pii = check_pii

    def check(self, text: str) -> GuardrailResult:
        """Run all output guardrail checks."""
        violations: list[str] = []

        # PII in output
        if self._check_pii:
            for pattern in PII_PATTERNS:
                if re.search(pattern, text):
                    violations.append(f"PII detected in output: {pattern}")

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
        )
