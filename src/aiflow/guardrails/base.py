"""Guardrail base classes and shared models.

Provides the abstract base for all guardrails (input, output, scope)
and the common result/violation data models used across the framework.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "GuardrailBase",
    "GuardrailResult",
    "GuardrailViolation",
    "Severity",
    "ScopeVerdict",
    "PIIMatch",
]


class Severity(str, enum.Enum):
    """Violation severity level."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ScopeVerdict(str, enum.Enum):
    """3-tier scope classification."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    DANGEROUS = "dangerous"


class PIIMatch(BaseModel):
    """A detected PII occurrence."""

    pattern_name: str
    matched_text: str
    start: int
    end: int


class GuardrailViolation(BaseModel):
    """Single guardrail violation with severity and metadata."""

    rule: str
    message: str
    severity: Severity = Severity.WARNING
    details: dict[str, Any] = Field(default_factory=dict)


class GuardrailResult(BaseModel):
    """Result of a guardrail check."""

    passed: bool = True
    violations: list[GuardrailViolation] = Field(default_factory=list)
    sanitized_text: str | None = None
    pii_matches: list[PIIMatch] = Field(default_factory=list)
    scope_verdict: ScopeVerdict | None = None
    hallucination_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_critical(self) -> bool:
        """Check if any violation is critical severity."""
        return any(v.severity == Severity.CRITICAL for v in self.violations)

    @property
    def violation_messages(self) -> list[str]:
        """Get flat list of violation message strings."""
        return [v.message for v in self.violations]


class GuardrailBase(ABC):
    """Abstract base class for all guardrails.

    Subclasses implement ``check()`` which validates text and returns
    a :class:`GuardrailResult`.
    """

    @abstractmethod
    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        """Run guardrail checks on the given text.

        Args:
            text: The text to validate.
            **kwargs: Additional context (e.g. sources for hallucination check).

        Returns:
            GuardrailResult with pass/fail and any violations.
        """
