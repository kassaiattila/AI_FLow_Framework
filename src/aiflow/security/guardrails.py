"""Input/output guardrails for content safety.

.. deprecated::
    This module is a backward-compatibility shim.  The canonical
    implementation lives in :mod:`aiflow.guardrails`.  Import from
    there for new code.
"""

from __future__ import annotations

from aiflow.guardrails.base import GuardrailResult as _NewResult
from aiflow.guardrails.input_guard import INJECTION_PATTERNS
from aiflow.guardrails.input_guard import InputGuard as _NewInputGuard
from aiflow.guardrails.output_guard import OutputGuard as _NewOutputGuard

__all__ = ["GuardrailResult", "InputGuardrail", "OutputGuardrail"]


class GuardrailResult:
    """Legacy result model — thin adapter over the new GuardrailResult.

    Preserves the old interface (``passed``, ``violations: list[str]``,
    ``sanitized_text``) so that existing callers keep working.
    """

    def __init__(
        self,
        passed: bool = True,
        violations: list[str] | None = None,
        sanitized_text: str | None = None,
    ) -> None:
        self.passed = passed
        self.violations: list[str] = violations or []
        self.sanitized_text = sanitized_text

    @classmethod
    def from_new(cls, result: _NewResult) -> GuardrailResult:
        """Convert a new-style result to the legacy format."""
        return cls(
            passed=result.passed,
            violations=result.violation_messages,
            sanitized_text=result.sanitized_text,
        )


class InputGuardrail:
    """Legacy input guardrail — delegates to :class:`aiflow.guardrails.InputGuard`."""

    def __init__(
        self,
        max_length: int = 10000,
        check_pii: bool = True,
        check_injection: bool = True,
    ) -> None:
        self._delegate = _NewInputGuard(
            max_length=max_length,
            check_pii=check_pii,
            check_injection=check_injection,
        )

    def check(self, text: str) -> GuardrailResult:
        """Run all input guardrail checks (legacy interface)."""
        result = self._delegate.check(text)
        return GuardrailResult.from_new(result)


class OutputGuardrail:
    """Legacy output guardrail — delegates to :class:`aiflow.guardrails.OutputGuard`."""

    def __init__(self, check_pii: bool = True) -> None:
        self._delegate = _NewOutputGuard(check_pii=check_pii, check_safety=False)

    def check(self, text: str) -> GuardrailResult:
        """Run all output guardrail checks (legacy interface)."""
        result = self._delegate.check(text)
        return GuardrailResult.from_new(result)


# Keep the old module-level constants importable for any direct references
FORBIDDEN_PATTERNS = [p for p, _ in INJECTION_PATTERNS]
