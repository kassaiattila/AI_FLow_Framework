"""
@test_registry:
    suite: guardrails-unit
    component: guardrails.scope_guard
    covers: [src/aiflow/guardrails/scope_guard.py, src/aiflow/guardrails/config.py]
    phase: A5
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [guardrails, scope, config, yaml]
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from aiflow.guardrails import (
    GuardrailConfig,
    ScopeGuard,
    ScopeVerdict,
    Severity,
    load_guardrail_config,
)


class TestScopeGuardInScope:
    """Tests for in-scope classification."""

    def test_allowed_topic_matches(self):
        guard = ScopeGuard(allowed_topics=["insurance", "law", "policy"])
        result = guard.check("Tell me about my insurance policy")
        assert result.passed is True
        assert result.scope_verdict == ScopeVerdict.IN_SCOPE
        assert "insurance" in result.metadata.get("matched_topics", [])

    def test_multiple_allowed_topics_match(self):
        guard = ScopeGuard(allowed_topics=["insurance", "law"])
        result = guard.check("Insurance law and policy details")
        assert result.passed is True
        assert result.scope_verdict == ScopeVerdict.IN_SCOPE
        matched = result.metadata.get("matched_topics", [])
        assert "insurance" in matched
        assert "law" in matched

    def test_no_allowed_topics_everything_passes(self):
        guard = ScopeGuard()
        result = guard.check("Anything at all")
        assert result.passed is True
        assert result.scope_verdict == ScopeVerdict.IN_SCOPE

    def test_case_insensitive_matching(self):
        guard = ScopeGuard(allowed_topics=["INSURANCE"])
        result = guard.check("Tell me about insurance")
        assert result.passed is True
        assert result.scope_verdict == ScopeVerdict.IN_SCOPE


class TestScopeGuardOutOfScope:
    """Tests for out-of-scope classification."""

    def test_no_allowed_topic_matches(self):
        guard = ScopeGuard(allowed_topics=["insurance", "law"])
        result = guard.check("What is the weather like today?")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.OUT_OF_SCOPE

    def test_blocked_topic_detected(self):
        guard = ScopeGuard(blocked_topics=["politics", "medical advice"])
        result = guard.check("What do you think about politics?")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.OUT_OF_SCOPE
        assert any(v.rule == "out_of_scope" for v in result.violations)

    def test_blocked_takes_priority_over_allowed(self):
        guard = ScopeGuard(
            allowed_topics=["insurance"],
            blocked_topics=["insurance fraud"],
        )
        result = guard.check("How to commit insurance fraud")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.OUT_OF_SCOPE


class TestScopeGuardDangerous:
    """Tests for dangerous content classification."""

    def test_dangerous_pattern_blocks(self):
        guard = ScopeGuard(dangerous_patterns=[r"how\s+to\s+(hack|break\s+into)"])
        result = guard.check("Tell me how to hack into a system")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.DANGEROUS
        assert any(v.severity == Severity.CRITICAL for v in result.violations)

    def test_dangerous_takes_priority_over_allowed(self):
        guard = ScopeGuard(
            allowed_topics=["security"],
            dangerous_patterns=[r"how\s+to\s+hack"],
        )
        result = guard.check("How to hack security systems")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.DANGEROUS

    def test_multiple_dangerous_patterns(self):
        guard = ScopeGuard(dangerous_patterns=[r"make\s+a?\s*bomb", r"steal\s+identity"])
        result = guard.check("How to steal identity from someone")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.DANGEROUS

    def test_safe_text_not_flagged(self):
        guard = ScopeGuard(dangerous_patterns=[r"how\s+to\s+hack"])
        result = guard.check("What is cybersecurity best practice?")
        assert result.scope_verdict != ScopeVerdict.DANGEROUS


class TestGuardrailConfig:
    """YAML config loading and guard instantiation."""

    def _write_config(self, data: dict) -> Path:
        """Write config to a temp YAML file and return its path."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            yaml.safe_dump(data, tmp)
        return Path(tmp.name)

    def test_load_valid_config(self):
        path = self._write_config(
            {
                "scope": {
                    "allowed_topics": ["insurance", "law"],
                    "dangerous_patterns": [r"hack\s+into"],
                },
                "input": {"max_length": 2000, "pii_masking": True},
                "output": {"hallucination_threshold": 0.5},
            }
        )
        config = load_guardrail_config(path)
        assert config.scope.allowed_topics == ["insurance", "law"]
        assert config.input.max_length == 2000
        assert config.output.hallucination_threshold == 0.5

    def test_build_guards_from_config(self):
        path = self._write_config(
            {
                "scope": {"allowed_topics": ["test"]},
                "input": {"max_length": 500},
                "output": {"hallucination_threshold": 0.4},
            }
        )
        config = load_guardrail_config(path)
        ig = config.build_input_guard()
        og = config.build_output_guard()
        sg = config.build_scope_guard()

        assert ig._max_length == 500
        assert og._hallucination_threshold == 0.4
        assert sg._allowed_topics == ["test"]

    def test_default_config(self):
        config = GuardrailConfig()
        ig = config.build_input_guard()
        assert ig._max_length == 10_000

    def test_missing_config_file(self):
        with pytest.raises(FileNotFoundError):
            load_guardrail_config("/nonexistent/guardrails.yaml")

    def test_invalid_yaml_content(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write("just a string, not a mapping")
        with pytest.raises(ValueError, match="expected mapping"):
            load_guardrail_config(tmp.name)

    def test_extra_injection_patterns_in_config(self):
        path = self._write_config(
            {
                "input": {
                    "extra_injection_patterns": [
                        ["evil_regex", "evil_label"],
                    ],
                },
            }
        )
        config = load_guardrail_config(path)
        ig = config.build_input_guard()
        result = ig.check("This has evil_regex in it")
        assert any(v.details.get("pattern_label") == "evil_label" for v in result.violations)


class TestBackwardCompat:
    """Verify the legacy security/guardrails.py shim still works."""

    def test_legacy_input_guardrail(self):
        from aiflow.security.guardrails import InputGuardrail

        g = InputGuardrail(max_length=50)
        result = g.check("Short text")
        assert result.passed is True
        assert isinstance(result.violations, list)

    def test_legacy_input_guardrail_violation(self):
        from aiflow.security.guardrails import InputGuardrail

        g = InputGuardrail(max_length=5)
        result = g.check("This is too long")
        assert result.passed is False
        assert len(result.violations) > 0
        assert isinstance(result.violations[0], str)

    def test_legacy_output_guardrail(self):
        from aiflow.security.guardrails import OutputGuardrail

        g = OutputGuardrail()
        result = g.check("Clean output text")
        assert result.passed is True

    def test_legacy_guardrail_result_type(self):
        from aiflow.security.guardrails import GuardrailResult

        r = GuardrailResult(passed=False, violations=["test violation"])
        assert r.passed is False
        assert r.violations == ["test violation"]

    def test_legacy_import_from_security_init(self):
        from aiflow.security import GuardrailResult, InputGuardrail, OutputGuardrail

        assert GuardrailResult is not None
        assert InputGuardrail is not None
        assert OutputGuardrail is not None
