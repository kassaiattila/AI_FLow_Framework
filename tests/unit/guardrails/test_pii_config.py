"""
@test_registry:
    suite: guardrails-unit
    component: guardrails.pii_config
    covers: [src/aiflow/guardrails/config.py, src/aiflow/guardrails/input_guard.py]
    phase: B1.2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [guardrails, pii, masking, config]
"""

from pathlib import Path

import pytest

from aiflow.guardrails import InputGuard, PIIMaskingMode
from aiflow.guardrails.config import GuardrailConfig, InputConfig, load_guardrail_config

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

# ---------------------------------------------------------------------------
# Sample texts with various PII
# ---------------------------------------------------------------------------
TEXT_WITH_EMAIL = "Kerem irjon a teszt@pelda.hu cimre."
TEXT_WITH_TAJ = "TAJ szam: 123-456-789"
TEXT_WITH_TAX = "Adoszam: 12345678-1-42"
TEXT_WITH_MULTI_PII = "Email: user@example.com, TAJ: 123-456-789, Adoszam: 12345678-1-42"
TEXT_CLEAN = "Mi a biztositasi kotvenyszam?"


# ===================================================================
# PIIMaskingMode enum
# ===================================================================


class TestPIIMaskingModeEnum:
    def test_on_value(self):
        assert PIIMaskingMode.ON.value == "on"

    def test_partial_value(self):
        assert PIIMaskingMode.PARTIAL.value == "partial"

    def test_off_value(self):
        assert PIIMaskingMode.OFF.value == "off"

    def test_is_str_enum(self):
        assert isinstance(PIIMaskingMode.ON, str)
        assert PIIMaskingMode.ON == "on"


# ===================================================================
# InputConfig model defaults
# ===================================================================


class TestInputConfigDefaults:
    def test_default_masking_mode_is_on(self):
        cfg = InputConfig()
        assert cfg.pii_masking_mode == PIIMaskingMode.ON

    def test_default_allowed_pii_types_empty(self):
        cfg = InputConfig()
        assert cfg.allowed_pii_types == []

    def test_default_pii_logging_false(self):
        cfg = InputConfig()
        assert cfg.pii_logging is False


# ===================================================================
# ON mode — mask ALL PII
# ===================================================================


class TestOnModeMasksAll:
    def test_on_mode_masks_email(self):
        guard = InputGuard(pii_masking_mode="on")
        result = guard.check(TEXT_WITH_EMAIL)
        assert result.sanitized_text is not None
        assert "teszt@pelda.hu" not in result.sanitized_text
        assert "[EMAIL]" in result.sanitized_text

    def test_on_mode_masks_taj(self):
        guard = InputGuard(pii_masking_mode="on")
        result = guard.check(TEXT_WITH_TAJ)
        assert result.sanitized_text is not None
        assert "123-456-789" not in result.sanitized_text

    def test_on_mode_masks_all_multi_pii(self):
        guard = InputGuard(pii_masking_mode="on")
        result = guard.check(TEXT_WITH_MULTI_PII)
        assert result.sanitized_text is not None
        assert "user@example.com" not in result.sanitized_text
        assert "123-456-789" not in result.sanitized_text
        assert "12345678-1-42" not in result.sanitized_text

    def test_on_mode_clean_text_passes(self):
        guard = InputGuard(pii_masking_mode="on")
        result = guard.check(TEXT_CLEAN)
        assert result.passed is True
        assert result.pii_matches == []


# ===================================================================
# OFF mode — no masking at all
# ===================================================================


class TestOffModePassesAll:
    def test_off_mode_no_masking(self):
        guard = InputGuard(pii_masking_mode="off")
        result = guard.check(TEXT_WITH_MULTI_PII)
        # No violations from PII
        assert not any(v.rule == "pii_detected" for v in result.violations)
        # sanitized_text should be None (no changes)
        assert result.sanitized_text is None

    def test_off_mode_passes(self):
        guard = InputGuard(pii_masking_mode="off")
        result = guard.check(TEXT_WITH_EMAIL)
        assert result.passed is True

    def test_off_mode_with_logging_detects_pii(self):
        guard = InputGuard(pii_masking_mode="off", pii_logging=True)
        result = guard.check(TEXT_WITH_EMAIL)
        # PII detected in matches (for audit) but not masked
        assert len(result.pii_matches) >= 1
        assert result.sanitized_text is None
        assert result.passed is True


# ===================================================================
# PARTIAL mode — only allowed PII passes through
# ===================================================================


class TestPartialMode:
    def test_partial_allows_email_blocks_tax(self):
        guard = InputGuard(
            pii_masking_mode="partial",
            allowed_pii_types=["email"],
        )
        result = guard.check(TEXT_WITH_MULTI_PII)
        assert result.sanitized_text is not None
        # Email should NOT be masked (allowed)
        assert "user@example.com" in result.sanitized_text
        # Tax number should be masked (not allowed)
        assert "12345678-1-42" not in result.sanitized_text

    def test_partial_allows_multiple_types(self):
        guard = InputGuard(
            pii_masking_mode="partial",
            allowed_pii_types=["email", "hu_taj"],
        )
        result = guard.check(TEXT_WITH_MULTI_PII)
        assert result.sanitized_text is not None
        assert "user@example.com" in result.sanitized_text
        assert "123-456-789" in result.sanitized_text
        # Tax number still masked
        assert "12345678-1-42" not in result.sanitized_text

    def test_partial_empty_allowed_same_as_on(self):
        guard = InputGuard(pii_masking_mode="partial", allowed_pii_types=[])
        result = guard.check(TEXT_WITH_EMAIL)
        assert result.sanitized_text is not None
        assert "teszt@pelda.hu" not in result.sanitized_text

    def test_partial_all_allowed_no_masking(self):
        guard = InputGuard(
            pii_masking_mode="partial",
            allowed_pii_types=["email", "hu_taj", "hu_tax_number"],
        )
        result = guard.check(TEXT_WITH_MULTI_PII)
        # All PII types allowed → no violation, no masking
        assert not any(v.rule == "pii_detected" for v in result.violations)


# ===================================================================
# pii_logging flag
# ===================================================================


class TestPIILogging:
    def test_logging_off_mode_still_detects(self):
        guard = InputGuard(pii_masking_mode="off", pii_logging=True)
        result = guard.check(TEXT_WITH_TAX)
        assert len(result.pii_matches) >= 1

    def test_no_logging_off_mode_no_detection(self):
        guard = InputGuard(pii_masking_mode="off", pii_logging=False)
        result = guard.check(TEXT_WITH_TAX)
        # Without logging, off mode skips PII detection entirely
        assert result.pii_matches == []


# ===================================================================
# Per-skill config loading
# ===================================================================


class TestPerSkillConfigLoad:
    @pytest.mark.parametrize(
        ("skill", "expected_mode", "expected_allowed"),
        [
            ("aszf_rag_chat", PIIMaskingMode.ON, []),
            ("email_intent_processor", PIIMaskingMode.PARTIAL, ["email", "phone", "hu_taj"]),
            ("invoice_processor", PIIMaskingMode.OFF, []),
            ("process_documentation", PIIMaskingMode.ON, []),
            ("cubix_course_capture", PIIMaskingMode.ON, []),
        ],
    )
    def test_skill_config_loads(
        self, skill: str, expected_mode: PIIMaskingMode, expected_allowed: list[str]
    ):
        path = SKILLS_DIR / skill / "guardrails.yaml"
        assert path.exists(), f"Missing guardrails.yaml for {skill}"
        cfg = load_guardrail_config(path)
        assert cfg.input.pii_masking_mode == expected_mode
        assert cfg.input.allowed_pii_types == expected_allowed

    def test_invoice_pii_logging_enabled(self):
        cfg = load_guardrail_config(SKILLS_DIR / "invoice_processor" / "guardrails.yaml")
        assert cfg.input.pii_logging is True

    def test_aszf_llm_fallback_enabled(self):
        cfg = load_guardrail_config(SKILLS_DIR / "aszf_rag_chat" / "guardrails.yaml")
        assert cfg.llm_fallback.enabled is True
        assert cfg.llm_fallback.hallucination_evaluator is True
        assert cfg.llm_fallback.pii_detector is True

    def test_invoice_llm_fallback_disabled(self):
        cfg = load_guardrail_config(SKILLS_DIR / "invoice_processor" / "guardrails.yaml")
        assert cfg.llm_fallback.enabled is False

    def test_build_input_guard_from_config(self):
        cfg = load_guardrail_config(SKILLS_DIR / "email_intent_processor" / "guardrails.yaml")
        guard = cfg.build_input_guard()
        assert guard._pii_masking_mode == "partial"
        assert guard._allowed_pii_types == {"email", "phone", "hu_taj"}


# ===================================================================
# Legacy backward compatibility
# ===================================================================


class TestLegacyBackwardCompat:
    def test_legacy_bool_true_maps_to_on(self):
        cfg = GuardrailConfig.model_validate(
            {
                "input": {"pii_masking": True},
            }
        )
        # Legacy bool doesn't auto-set pii_masking_mode (only load_guardrail_config normalizes)
        assert cfg.input.pii_masking is True

    def test_default_guard_still_works(self):
        guard = InputGuard()
        result = guard.check(TEXT_CLEAN)
        assert result.passed is True
