"""Hybrid classifier - combines sklearn ML and LLM-based classification.

Strategy:
1. Run sklearn classifier (fast, cheap)
2. If confidence < threshold, also run LLM classifier
3. Combine results with configurable strategy (sklearn_first, llm_first, ensemble)
"""
from __future__ import annotations

from typing import Any

import structlog
from skills.email_intent_processor.models import IntentResult

__all__ = ["HybridClassifier"]

logger = structlog.get_logger(__name__)


class HybridClassifier:
    """Combines sklearn and LLM classifiers with configurable strategy.

    Strategies:
        sklearn_first: Use sklearn, fallback to LLM if low confidence
        llm_first: Use LLM, fallback to sklearn if low confidence
        ensemble: Run both, weighted average
        sklearn_only: Only sklearn
        llm_only: Only LLM
    """

    def __init__(
        self,
        sklearn_classifier: Any | None = None,
        llm_classifier: Any | None = None,
        strategy: str = "sklearn_first",
        confidence_threshold: float = 0.6,
        sklearn_weight: float = 0.4,
        llm_weight: float = 0.6,
    ) -> None:
        self.sklearn_classifier = sklearn_classifier
        self.llm_classifier = llm_classifier
        self.strategy = strategy
        self.confidence_threshold = confidence_threshold
        self.sklearn_weight = sklearn_weight
        self.llm_weight = llm_weight

    async def classify(
        self,
        text: str,
        subject: str = "",
        schema_intents: list[dict] | None = None,
    ) -> IntentResult:
        """Classify text using the configured strategy."""
        full_text = f"{subject}\n\n{text}" if subject else text

        if self.strategy == "sklearn_only":
            return await self._classify_sklearn(full_text, schema_intents)
        elif self.strategy == "llm_only":
            return await self._classify_llm(text, subject, schema_intents)
        elif self.strategy == "sklearn_first":
            return await self._sklearn_first(text, subject, full_text, schema_intents)
        elif self.strategy == "llm_first":
            return await self._llm_first(text, subject, full_text, schema_intents)
        elif self.strategy == "ensemble":
            return await self._ensemble(text, subject, full_text, schema_intents)
        else:
            logger.warning("unknown_strategy", strategy=self.strategy)
            return await self._sklearn_first(text, subject, full_text, schema_intents)

    async def _sklearn_first(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_intents: list[dict] | None,
    ) -> IntentResult:
        """Use sklearn first, fallback to LLM if low confidence."""
        sklearn_result = await self._classify_sklearn(full_text, schema_intents)

        if sklearn_result.confidence >= self.confidence_threshold:
            sklearn_result.method = "sklearn"
            return sklearn_result

        logger.info(
            "sklearn_low_confidence",
            intent=sklearn_result.intent_id,
            confidence=sklearn_result.confidence,
            threshold=self.confidence_threshold,
        )

        if self.llm_classifier is None:
            sklearn_result.method = "sklearn_only_no_llm"
            return sklearn_result

        llm_result = await self._classify_llm(text, subject, schema_intents)
        return self._merge_results(sklearn_result, llm_result, prefer="llm")

    async def _llm_first(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_intents: list[dict] | None,
    ) -> IntentResult:
        """Use LLM first, fallback to sklearn if low confidence."""
        if self.llm_classifier is None:
            return await self._classify_sklearn(full_text, schema_intents)

        llm_result = await self._classify_llm(text, subject, schema_intents)

        if llm_result.confidence >= self.confidence_threshold:
            llm_result.method = "llm"
            return llm_result

        sklearn_result = await self._classify_sklearn(full_text, schema_intents)
        return self._merge_results(sklearn_result, llm_result, prefer="sklearn")

    async def _ensemble(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_intents: list[dict] | None,
    ) -> IntentResult:
        """Run both classifiers and merge with weighted average."""
        sklearn_result = await self._classify_sklearn(full_text, schema_intents)

        if self.llm_classifier is None:
            sklearn_result.method = "sklearn_only_no_llm"
            return sklearn_result

        llm_result = await self._classify_llm(text, subject, schema_intents)

        # If both agree, boost confidence
        if sklearn_result.intent_id == llm_result.intent_id:
            combined_confidence = min(
                1.0,
                sklearn_result.confidence * self.sklearn_weight
                + llm_result.confidence * self.llm_weight
                + 0.1,  # Agreement bonus
            )
            return IntentResult(
                intent_id=sklearn_result.intent_id,
                intent_display_name=llm_result.intent_display_name or sklearn_result.intent_display_name,
                confidence=round(combined_confidence, 4),
                sub_intent=llm_result.sub_intent,
                method="ensemble_agree",
                sklearn_intent=sklearn_result.intent_id,
                sklearn_confidence=sklearn_result.confidence,
                llm_intent=llm_result.intent_id,
                llm_confidence=llm_result.confidence,
                reasoning=llm_result.reasoning,
            )

        # Disagreement: pick higher weighted confidence
        sklearn_score = sklearn_result.confidence * self.sklearn_weight
        llm_score = llm_result.confidence * self.llm_weight
        prefer = "sklearn" if sklearn_score > llm_score else "llm"
        return self._merge_results(sklearn_result, llm_result, prefer=prefer)

    async def _classify_sklearn(
        self,
        text: str,
        schema_intents: list[dict] | None,
    ) -> IntentResult:
        """Run sklearn classifier."""
        if self.sklearn_classifier is None:
            return IntentResult(
                intent_id="unknown",
                confidence=0.0,
                method="sklearn_unavailable",
            )

        try:
            result = self.sklearn_classifier.predict(text)
            return IntentResult(
                intent_id=result["intent"],
                confidence=result.get("confidence", 0.5),
                method="sklearn",
                sklearn_intent=result["intent"],
                sklearn_confidence=result.get("confidence", 0.5),
                alternatives=result.get("alternatives", []),
            )
        except Exception as e:
            logger.error("sklearn_classify_failed", error=str(e))
            return IntentResult(
                intent_id="unknown",
                confidence=0.0,
                method="sklearn_error",
            )

    async def _classify_llm(
        self,
        text: str,
        subject: str,
        schema_intents: list[dict] | None,
    ) -> IntentResult:
        """Run LLM classifier."""
        if self.llm_classifier is None:
            return IntentResult(
                intent_id="unknown",
                confidence=0.0,
                method="llm_unavailable",
            )

        try:
            return await self.llm_classifier.classify(text, subject, schema_intents)
        except Exception as e:
            logger.error("llm_classify_failed", error=str(e))
            return IntentResult(
                intent_id="unknown",
                confidence=0.0,
                method="llm_error",
            )

    def _merge_results(
        self,
        sklearn_result: IntentResult,
        llm_result: IntentResult,
        prefer: str = "llm",
    ) -> IntentResult:
        """Merge sklearn and LLM results, preferring one source."""
        primary = llm_result if prefer == "llm" else sklearn_result
        secondary = sklearn_result if prefer == "llm" else llm_result

        return IntentResult(
            intent_id=primary.intent_id,
            intent_display_name=primary.intent_display_name or secondary.intent_display_name,
            confidence=round(primary.confidence, 4),
            sub_intent=primary.sub_intent or secondary.sub_intent,
            method=f"hybrid_{prefer}",
            sklearn_intent=sklearn_result.intent_id,
            sklearn_confidence=sklearn_result.confidence,
            llm_intent=llm_result.intent_id,
            llm_confidence=llm_result.confidence,
            alternatives=primary.alternatives or secondary.alternatives,
            reasoning=llm_result.reasoning,
        )
