"""AIFlow Guardrail Framework.

Provides input validation, output safety, and scope enforcement
for LLM-powered skills.

Usage::

    from aiflow.guardrails import InputGuard, OutputGuard, ScopeGuard

    guard = InputGuard(max_length=2000, pii_masking=True)
    result = guard.check(user_input)
    if not result.passed:
        print(result.violation_messages)
"""

from aiflow.guardrails.base import (
    GuardrailBase,
    GuardrailResult,
    GuardrailViolation,
    PIIMatch,
    ScopeVerdict,
    Severity,
)
from aiflow.guardrails.config import GuardrailConfig, load_guardrail_config
from aiflow.guardrails.input_guard import InputGuard
from aiflow.guardrails.output_guard import OutputGuard
from aiflow.guardrails.scope_guard import ScopeGuard

__all__ = [
    # Base
    "GuardrailBase",
    "GuardrailResult",
    "GuardrailViolation",
    "PIIMatch",
    "Severity",
    "ScopeVerdict",
    # Guards
    "InputGuard",
    "OutputGuard",
    "ScopeGuard",
    # Config
    "GuardrailConfig",
    "load_guardrail_config",
]
