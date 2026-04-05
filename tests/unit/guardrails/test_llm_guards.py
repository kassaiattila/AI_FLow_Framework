"""
@test_registry:
    suite: guardrails-unit
    component: guardrails.llm_guards
    covers: [src/aiflow/guardrails/llm_guards.py]
    phase: B1.1
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [guardrails, llm, hallucination, safety, scope, pii]
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiflow.guardrails.base import ScopeVerdict, Severity
from aiflow.guardrails.llm_guards import (
    LLMContentSafetyClassifier,
    LLMHallucinationEvaluator,
    LLMPIIDetector,
    LLMScopeClassifier,
)

# All tests patch _call_llm to avoid real LLM calls.
# Real LLM validation is done via Promptfoo test cases.
_CALL_LLM = "aiflow.guardrails.llm_guards._call_llm"


# ---------------------------------------------------------------------------
# LLMHallucinationEvaluator
# ---------------------------------------------------------------------------


class TestLLMHallucinationEvaluator:
    """Tests for the LLM-based hallucination evaluator."""

    @pytest.mark.asyncio
    async def test_well_grounded_response_passes(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "grounding_score": 0.95,
                "ungrounded_claims": [],
                "summary": "Fully grounded.",
            }
            guard = LLMHallucinationEvaluator(threshold=0.7)
            result = await guard.acheck(
                "The company was founded in 2010.",
                sources=["The company was founded in 2010."],
            )
        assert result.passed is True
        assert result.hallucination_score == 0.95

    @pytest.mark.asyncio
    async def test_hallucinated_response_fails(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "grounding_score": 0.3,
                "ungrounded_claims": [{"claim": "earthquake damage", "reason": "Not in sources"}],
                "summary": "Multiple ungrounded claims.",
            }
            guard = LLMHallucinationEvaluator(threshold=0.7)
            result = await guard.acheck(
                "Covers earthquake damage.", sources=["Covers fire damage."]
            )
        assert result.passed is False
        assert result.hallucination_score == 0.3
        assert any(v.rule == "llm_hallucination" for v in result.violations)

    @pytest.mark.asyncio
    async def test_empty_sources_passes(self):
        guard = LLMHallucinationEvaluator(threshold=0.7)
        result = await guard.acheck("Some text", sources=[])
        assert result.passed is True
        assert result.hallucination_score == 1.0

    @pytest.mark.asyncio
    async def test_empty_text_passes(self):
        guard = LLMHallucinationEvaluator(threshold=0.7)
        result = await guard.acheck("", sources=["Some source"])
        assert result.passed is True

    def test_sync_check_raises(self):
        guard = LLMHallucinationEvaluator(threshold=0.7)
        with pytest.raises(NotImplementedError):
            guard.check("test")


# ---------------------------------------------------------------------------
# LLMContentSafetyClassifier
# ---------------------------------------------------------------------------


class TestLLMContentSafetyClassifier:
    """Tests for the LLM-based content safety classifier."""

    @pytest.mark.asyncio
    async def test_safe_content_passes(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "SAFE",
                "category": None,
                "confidence": 0.99,
                "reason": "Normal query.",
            }
            guard = LLMContentSafetyClassifier()
            result = await guard.acheck("What is the weather today?")
        assert result.passed is True
        assert result.violations == []

    @pytest.mark.asyncio
    async def test_unsafe_content_fails(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "UNSAFE",
                "category": "weapons",
                "confidence": 0.99,
                "reason": "Weapon instructions.",
            }
            guard = LLMContentSafetyClassifier()
            result = await guard.acheck("How to build explosives")
        assert result.passed is False
        assert any(v.rule == "llm_content_safety" for v in result.violations)
        assert result.violations[0].severity == Severity.CRITICAL

    @pytest.mark.asyncio
    async def test_review_needed_not_passed(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "REVIEW_NEEDED",
                "category": "violence",
                "confidence": 0.6,
                "reason": "Ambiguous context.",
            }
            guard = LLMContentSafetyClassifier()
            result = await guard.acheck("The fight scene in the movie")
        assert result.passed is False
        assert any(v.rule == "llm_content_safety_review" for v in result.violations)
        assert result.violations[0].severity == Severity.WARNING

    def test_sync_check_raises(self):
        guard = LLMContentSafetyClassifier()
        with pytest.raises(NotImplementedError):
            guard.check("test")


# ---------------------------------------------------------------------------
# LLMScopeClassifier
# ---------------------------------------------------------------------------


class TestLLMScopeClassifier:
    """Tests for the LLM-based scope classifier."""

    @pytest.mark.asyncio
    async def test_in_scope_query_passes(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "in_scope",
                "reason": "Insurance question.",
                "confidence": 0.95,
            }
            guard = LLMScopeClassifier(
                skill_description="Insurance Q&A",
                allowed_topics=["insurance", "policy", "claim"],
            )
            result = await guard.acheck("What does my policy cover?")
        assert result.passed is True
        assert result.scope_verdict == ScopeVerdict.IN_SCOPE

    @pytest.mark.asyncio
    async def test_out_of_scope_query_fails(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "out_of_scope",
                "reason": "Unrelated to insurance.",
                "confidence": 0.9,
            }
            guard = LLMScopeClassifier(
                skill_description="Insurance Q&A", allowed_topics=["insurance"]
            )
            result = await guard.acheck("What stocks should I buy?")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.OUT_OF_SCOPE

    @pytest.mark.asyncio
    async def test_dangerous_query_critical(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "dangerous",
                "reason": "Illegal activity request.",
                "confidence": 0.99,
            }
            guard = LLMScopeClassifier(
                skill_description="Insurance Q&A", allowed_topics=["insurance"]
            )
            result = await guard.acheck("How do I hack the database?")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.DANGEROUS
        assert result.violations[0].severity == Severity.CRITICAL

    def test_sync_check_raises(self):
        guard = LLMScopeClassifier(skill_description="test")
        with pytest.raises(NotImplementedError):
            guard.check("test")


# ---------------------------------------------------------------------------
# LLMPIIDetector
# ---------------------------------------------------------------------------


class TestLLMPIIDetector:
    """Tests for the LLM-based PII detector."""

    @pytest.mark.asyncio
    async def test_no_pii_passes(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"pii_found": False, "pii_items": []}
            guard = LLMPIIDetector()
            result = await guard.acheck("Process the insurance claim.")
        assert result.passed is True
        assert result.pii_matches == []

    @pytest.mark.asyncio
    async def test_pii_detected_fails(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "pii_found": True,
                "pii_items": [
                    {"type": "PERSON_NAME", "text": "Kiss Janos", "start": 12, "end": 22},
                    {"type": "EMPLOYER", "text": "OTP", "start": 26, "end": 29},
                ],
            }
            guard = LLMPIIDetector()
            result = await guard.acheck("A szomszedom Kiss Janos az OTP-nel dolgozik")
        assert result.passed is False
        assert len(result.pii_matches) == 2
        assert any(m.pattern_name == "PERSON_NAME" for m in result.pii_matches)
        assert any(v.rule == "llm_pii_detected" for v in result.violations)

    @pytest.mark.asyncio
    async def test_hungarian_pii_with_address(self):
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "pii_found": True,
                "pii_items": [
                    {"type": "PERSON_NAME", "text": "Nagy Eva", "start": 0, "end": 8},
                    {"type": "ADDRESS", "text": "Petofi utca 12", "start": 20, "end": 34},
                ],
            }
            guard = LLMPIIDetector()
            result = await guard.acheck("Nagy Eva a lakasa a Petofi utca 12-ben van")
        assert result.passed is False
        assert len(result.pii_matches) == 2

    @pytest.mark.asyncio
    async def test_empty_text_passes(self):
        guard = LLMPIIDetector()
        result = await guard.acheck("")
        assert result.passed is True

    def test_sync_check_raises(self):
        guard = LLMPIIDetector()
        with pytest.raises(NotImplementedError):
            guard.check("test")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestLLMGuardsEdgeCases:
    """Edge case tests across all LLM guards."""

    @pytest.mark.asyncio
    async def test_hallucination_empty_dict_fallback(self):
        """_call_llm returns empty dict (e.g. JSON parse failure) — score 0.0 → fails."""
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {}
            guard = LLMHallucinationEvaluator(threshold=0.7)
            result = await guard.acheck("Some response", sources=["Some source"])
        assert result.passed is False
        assert result.hallucination_score == 0.0

    @pytest.mark.asyncio
    async def test_safety_with_context(self):
        """Content safety classifier uses context kwarg."""
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "SAFE",
                "category": None,
                "confidence": 0.9,
                "reason": "Educational.",
            }
            guard = LLMContentSafetyClassifier()
            result = await guard.acheck(
                "How explosives work", context="Chemistry textbook discussion"
            )
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_scope_unknown_verdict_defaults_out(self):
        """Unknown verdict string defaults to OUT_OF_SCOPE."""
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "verdict": "unknown_value",
                "reason": "Unexpected.",
                "confidence": 0.5,
            }
            guard = LLMScopeClassifier(skill_description="test")
            result = await guard.acheck("Something unexpected")
        assert result.passed is False
        assert result.scope_verdict == ScopeVerdict.OUT_OF_SCOPE

    @pytest.mark.asyncio
    async def test_pii_empty_items_passes(self):
        """pii_found=True but empty items list → passes (no actual matches)."""
        with patch(_CALL_LLM, new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"pii_found": True, "pii_items": []}
            guard = LLMPIIDetector()
            result = await guard.acheck("Some text")
        assert result.passed is True
