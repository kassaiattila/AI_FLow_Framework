"""
@test_registry:
    suite: guardrails-unit
    component: guardrails.output_guard
    covers: [src/aiflow/guardrails/output_guard.py]
    phase: A5
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [guardrails, output, safety, hallucination, pii]
"""

from aiflow.guardrails import OutputGuard, Severity


class TestOutputGuardBasic:
    """Basic output validation tests."""

    def test_clean_output_passes(self):
        guard = OutputGuard()
        result = guard.check("Here is the information you requested about the policy.")
        assert result.passed is True

    def test_empty_output_passes(self):
        guard = OutputGuard()
        result = guard.check("")
        assert result.passed is True


class TestOutputGuardPII:
    """PII leak detection in LLM output."""

    def test_email_leak_detected(self):
        guard = OutputGuard()
        result = guard.check("The customer email is john@example.com as shown in records.")
        assert result.passed is False
        assert any(m.pattern_name == "email" for m in result.pii_matches)

    def test_ssn_leak_detected(self):
        guard = OutputGuard()
        result = guard.check("Found SSN: 123-45-6789 in the document.")
        assert result.passed is False
        assert any(m.pattern_name == "us_ssn" for m in result.pii_matches)

    def test_hu_bank_account_leak(self):
        guard = OutputGuard()
        result = guard.check("Bankszamlaszam: 11773016-01234567-00000000")
        assert result.passed is False
        assert any(m.pattern_name == "hu_bank_account" for m in result.pii_matches)

    def test_pii_check_disabled(self):
        guard = OutputGuard(check_pii=False)
        result = guard.check("Email: test@example.com")
        assert result.pii_matches == []

    def test_no_pii_in_clean_output(self):
        guard = OutputGuard()
        result = guard.check("The insurance policy covers fire and flood damage.")
        assert result.pii_matches == []


class TestOutputGuardSafety:
    """Content safety pattern detection."""

    def test_violence_incitement_blocked(self):
        guard = OutputGuard()
        result = guard.check("You should kill yourself for asking that")
        assert result.passed is False
        assert any(v.rule == "content_safety" for v in result.violations)
        assert any(v.severity == Severity.CRITICAL for v in result.violations)

    def test_weapon_instructions_blocked(self):
        guard = OutputGuard()
        result = guard.check("Here is how to make a bomb at home")
        assert result.passed is False
        assert any(
            "weapon_instructions" in v.details.get("pattern_label", "") for v in result.violations
        )

    def test_xss_in_output_blocked(self):
        guard = OutputGuard()
        result = guard.check('Response: <script>alert("xss")</script>')
        assert result.passed is False
        assert any("xss_in_output" in v.details.get("pattern_label", "") for v in result.violations)

    def test_safe_content_passes(self):
        guard = OutputGuard()
        result = guard.check("Your insurance claim has been processed successfully.")
        assert result.passed is True

    def test_safety_disabled(self):
        guard = OutputGuard(check_safety=False)
        result = guard.check("how to make a bomb")
        assert not any(v.rule == "content_safety" for v in result.violations)


class TestOutputGuardHallucination:
    """Hallucination / grounding score tests."""

    def test_well_grounded_response(self):
        sources = ["The policy covers fire damage up to 10 million HUF."]
        guard = OutputGuard(hallucination_threshold=0.2)
        result = guard.check(
            "The policy covers fire damage up to 10 million HUF.",
            sources=sources,
        )
        assert result.hallucination_score is not None
        assert result.hallucination_score >= 0.2
        assert not any(v.rule == "hallucination_risk" for v in result.violations)

    def test_ungrounded_response_flagged(self):
        sources = ["The policy covers fire damage."]
        guard = OutputGuard(hallucination_threshold=0.8)
        result = guard.check(
            "Aliens built the pyramids and the moon is made of cheese.",
            sources=sources,
        )
        assert result.hallucination_score is not None
        assert result.hallucination_score < 0.8
        assert any(v.rule == "hallucination_risk" for v in result.violations)

    def test_no_sources_no_hallucination_check(self):
        guard = OutputGuard()
        result = guard.check("Some response text")
        assert result.hallucination_score is None
        assert not any(v.rule == "hallucination_risk" for v in result.violations)

    def test_empty_sources_low_score(self):
        guard = OutputGuard(hallucination_threshold=0.1)
        result = guard.check("Some response", sources=[])
        assert result.hallucination_score == 0.0

    def test_very_short_response_high_score(self):
        guard = OutputGuard()
        result = guard.check("OK.", sources=["Some source text"])
        assert result.hallucination_score is not None
        # Very short responses get score 1.0 (cannot assess)
        assert result.hallucination_score == 1.0
