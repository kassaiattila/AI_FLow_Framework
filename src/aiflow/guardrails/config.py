"""YAML-based guardrail configuration loader.

Loads per-skill guardrail settings from a YAML file and instantiates
the corresponding guard objects (InputGuard, OutputGuard, ScopeGuard).
"""

from __future__ import annotations

import enum
from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field

from aiflow.guardrails.input_guard import InputGuard
from aiflow.guardrails.output_guard import OutputGuard
from aiflow.guardrails.scope_guard import ScopeGuard

__all__ = ["GuardrailConfig", "PIIMaskingMode", "load_guardrail_config"]

logger = structlog.get_logger(__name__)


class PIIMaskingMode(str, enum.Enum):
    """PII masking strategy per skill.

    ON      — mask all PII (default, safest)
    PARTIAL — only mask PII types NOT in allowed_pii_types
    OFF     — no masking at all (e.g. invoice processing needs full PII)
    """

    ON = "on"
    PARTIAL = "partial"
    OFF = "off"


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
    pii_masking_mode: PIIMaskingMode = PIIMaskingMode.ON
    allowed_pii_types: list[str] = Field(default_factory=list)
    pii_logging: bool = False
    allowed_languages: list[str] | None = None
    extra_injection_patterns: list[list[str]] = Field(default_factory=list)


class OutputConfig(BaseModel):
    """Output guard configuration section."""

    check_pii: bool = True
    check_safety: bool = True
    hallucination_threshold: float = 0.3
    require_citation: bool = False


class LLMFallbackConfig(BaseModel):
    """LLM-based guardrail fallback configuration.

    When rule-based guards are uncertain, LLM guards provide
    a more precise (but slower/$) second opinion.
    """

    enabled: bool = False
    hallucination_evaluator: bool = False
    content_safety_classifier: bool = False
    scope_classifier: bool = False
    pii_detector: bool = False
    confidence_threshold: float = 0.7
    model: str = "openai/gpt-4o-mini"
    timeout: int = 15


class GuardrailConfig(BaseModel):
    """Top-level guardrail configuration (maps to YAML structure)."""

    scope: ScopeConfig = Field(default_factory=ScopeConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm_fallback: LLMFallbackConfig = Field(default_factory=LLMFallbackConfig)

    def build_input_guard(self) -> InputGuard:
        """Instantiate an InputGuard from this configuration."""
        extra = [(p[0], p[1]) for p in self.input.extra_injection_patterns if len(p) >= 2]
        return InputGuard(
            max_length=self.input.max_length,
            check_pii=self.input.check_pii,
            pii_masking=self.input.pii_masking,
            pii_masking_mode=self.input.pii_masking_mode,
            allowed_pii_types=self.input.allowed_pii_types,
            pii_logging=self.input.pii_logging,
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


def _normalize_pii_masking(data: dict) -> None:
    """Convert YAML pii_masking string/bool to PIIMaskingMode + legacy bool.

    Handles both new format (``pii_masking: "on"/"partial"/"off"``)
    and legacy format (``pii_masking: true/false``).
    """
    input_cfg = data.get("input")
    if not isinstance(input_cfg, dict):
        return

    raw = input_cfg.get("pii_masking")
    if raw is None:
        return

    if isinstance(raw, bool):
        # Legacy: true → ON + masking enabled, false → OFF
        input_cfg["pii_masking_mode"] = PIIMaskingMode.ON.value if raw else PIIMaskingMode.OFF.value
        input_cfg["pii_masking"] = raw
    elif isinstance(raw, str) and raw in {"on", "partial", "off"}:
        input_cfg["pii_masking_mode"] = raw
        input_cfg["pii_masking"] = raw != "off"
    # Map allowed_pii → allowed_pii_types for YAML convenience
    if "allowed_pii" in input_cfg and "allowed_pii_types" not in input_cfg:
        input_cfg["allowed_pii_types"] = input_cfg.pop("allowed_pii")


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

    _normalize_pii_masking(data)

    config = GuardrailConfig.model_validate(data)
    logger.info("guardrail_config_loaded", path=str(path))
    return config
