"""YAML-based guardrail configuration loader.

Loads per-skill guardrail settings from a YAML file and instantiates
the corresponding guard objects (InputGuard, OutputGuard, ScopeGuard).
"""

from __future__ import annotations

from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field

from aiflow.guardrails.input_guard import InputGuard
from aiflow.guardrails.output_guard import OutputGuard
from aiflow.guardrails.scope_guard import ScopeGuard

__all__ = ["GuardrailConfig", "load_guardrail_config"]

logger = structlog.get_logger(__name__)


class ScopeConfig(BaseModel):
    """Scope guard configuration section."""

    allowed_topics: list[str] = Field(default_factory=list)
    blocked_topics: list[str] = Field(default_factory=list)
    dangerous_patterns: list[str] = Field(default_factory=list)


class InputConfig(BaseModel):
    """Input guard configuration section."""

    max_length: int = 10_000
    check_injection: bool = True
    check_pii: bool = True
    pii_masking: bool = False
    allowed_languages: list[str] | None = None
    extra_injection_patterns: list[list[str]] = Field(default_factory=list)


class OutputConfig(BaseModel):
    """Output guard configuration section."""

    check_pii: bool = True
    check_safety: bool = True
    hallucination_threshold: float = 0.3
    require_citation: bool = False


class GuardrailConfig(BaseModel):
    """Top-level guardrail configuration (maps to YAML structure)."""

    scope: ScopeConfig = Field(default_factory=ScopeConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    def build_input_guard(self) -> InputGuard:
        """Instantiate an InputGuard from this configuration."""
        extra = [(p[0], p[1]) for p in self.input.extra_injection_patterns if len(p) >= 2]
        return InputGuard(
            max_length=self.input.max_length,
            check_pii=self.input.check_pii,
            pii_masking=self.input.pii_masking,
            check_injection=self.input.check_injection,
            allowed_languages=self.input.allowed_languages,
            injection_patterns=extra or None,
        )

    def build_output_guard(self) -> OutputGuard:
        """Instantiate an OutputGuard from this configuration."""
        return OutputGuard(
            check_pii=self.output.check_pii,
            check_safety=self.output.check_safety,
            hallucination_threshold=self.output.hallucination_threshold,
        )

    def build_scope_guard(self) -> ScopeGuard:
        """Instantiate a ScopeGuard from this configuration."""
        return ScopeGuard(
            allowed_topics=self.scope.allowed_topics or None,
            blocked_topics=self.scope.blocked_topics or None,
            dangerous_patterns=self.scope.dangerous_patterns or None,
        )


def load_guardrail_config(path: str | Path) -> GuardrailConfig:
    """Load guardrail configuration from a YAML file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Parsed GuardrailConfig instance.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the YAML content is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Guardrail config not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid guardrail config (expected mapping): {path}")

    config = GuardrailConfig.model_validate(data)
    logger.info("guardrail_config_loaded", path=str(path))
    return config
