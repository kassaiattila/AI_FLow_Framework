"""Classifier service — configurable hybrid text classification.

Generalizes email_intent_processor's HybridClassifier into a config-driven
classification service. Works for ANY text classification task (emails,
tickets, documents, support requests, etc.) via schema_labels.

Strategies:
    sklearn_first: Keyword-based fast path, fallback to LLM if low confidence
    llm_first: LLM first, fallback to keyword-based if low confidence
    ensemble: Run both, weighted average + agreement bonus
    sklearn_only: Only keyword-based scoring
    llm_only: Only LLM classification
"""

from __future__ import annotations

import json
import math
import re
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "ClassificationStrategy",
    "ClassificationResult",
    "ClassifierConfig",
    "ClassifierService",
]

logger = structlog.get_logger(__name__)


class ClassificationStrategy(str, Enum):
    """Available classification strategies."""

    SKLEARN_FIRST = "sklearn_first"
    LLM_FIRST = "llm_first"
    ENSEMBLE = "ensemble"
    SKLEARN_ONLY = "sklearn_only"
    LLM_ONLY = "llm_only"


class ClassificationResult(BaseModel):
    """Result of a text classification."""

    label: str = ""
    display_name: str = ""
    confidence: float = 0.0
    method: str = ""  # "keywords", "llm", "hybrid_llm", "hybrid_keywords", "ensemble_agree"
    sub_label: str | None = ""
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""
    sklearn_label: str | None = ""
    sklearn_confidence: float = 0.0
    llm_label: str | None = ""
    llm_confidence: float = 0.0


class ClassifierConfig(ServiceConfig):
    """Service-level configuration for the Classifier."""

    strategy: ClassificationStrategy = ClassificationStrategy.SKLEARN_FIRST
    confidence_threshold: float = 0.6
    sklearn_weight: float = 0.4
    llm_weight: float = 0.6
    llm_model: str = "openai/gpt-4o-mini"
    llm_temperature: float = 0.1
    max_tokens: int = 500


class ClassifierService(BaseService):
    """Configurable hybrid text classification service.

    Uses keyword-based scoring as the fast path (replaces sklearn TF-IDF
    for the general case — works from schema_labels alone, no trained model
    needed) and LLM for higher-accuracy classification.

    The schema_labels parameter makes this service domain-agnostic: pass
    email intents, ticket categories, document types, or any other label
    set and the service classifies accordingly.
    """

    def __init__(
        self,
        config: ClassifierConfig | None = None,
        models_client: Any | None = None,
        prompt_manager: Any | None = None,
    ) -> None:
        self._cls_config = config or ClassifierConfig()
        self._models_client = models_client
        self._prompt_manager = prompt_manager
        super().__init__(self._cls_config)

    @property
    def service_name(self) -> str:
        return "classifier"

    @property
    def service_description(self) -> str:
        return "Configurable hybrid text classification (keywords + LLM)"

    @property
    def strategy(self) -> ClassificationStrategy:
        """Current default classification strategy."""
        return self._cls_config.strategy

    @property
    def confidence_threshold(self) -> float:
        """Confidence threshold below which fallback is triggered."""
        return self._cls_config.confidence_threshold

    async def _start(self) -> None:
        self._logger.info(
            "classifier_config",
            strategy=self._cls_config.strategy.value,
            threshold=self._cls_config.confidence_threshold,
            llm_model=self._cls_config.llm_model,
        )

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    async def classify(
        self,
        text: str,
        subject: str = "",
        schema_labels: list[dict[str, Any]] | None = None,
        strategy: str | None = None,
    ) -> ClassificationResult:
        """Classify text using the configured (or overridden) strategy.

        Args:
            text: The main text to classify.
            subject: Optional subject/title (prepended for keyword scoring).
            schema_labels: List of label definitions, each with keys:
                - id (str): unique label identifier
                - display_name (str): human-readable name
                - description (str): what this label means
                - keywords (list[str]): trigger keywords for fast matching
                - examples (list[str]): example texts for LLM few-shot
            strategy: Override the default strategy for this call.

        Returns:
            ClassificationResult with the winning label and metadata.
        """
        active_strategy = (
            ClassificationStrategy(strategy) if strategy else self._cls_config.strategy
        )
        labels = schema_labels or []
        full_text = f"{subject}\n\n{text}" if subject else text

        if active_strategy == ClassificationStrategy.SKLEARN_ONLY:
            return await self._classify_keywords(full_text, labels)

        if active_strategy == ClassificationStrategy.LLM_ONLY:
            return await self._classify_llm(text, subject, labels)

        if active_strategy == ClassificationStrategy.SKLEARN_FIRST:
            return await self._keywords_first(text, subject, full_text, labels)

        if active_strategy == ClassificationStrategy.LLM_FIRST:
            return await self._llm_first(text, subject, full_text, labels)

        if active_strategy == ClassificationStrategy.ENSEMBLE:
            return await self._ensemble(text, subject, full_text, labels)

        # Fallback to keywords_first for unknown strategy values
        self._logger.warning("unknown_strategy", strategy=active_strategy)
        return await self._keywords_first(text, subject, full_text, labels)

    # ------------------------------------------------------------------
    # Strategy orchestrators
    # ------------------------------------------------------------------

    async def _keywords_first(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_labels: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Keyword-based first, fallback to LLM if low confidence."""
        kw_result = await self._classify_keywords(full_text, schema_labels)

        if kw_result.confidence >= self._cls_config.confidence_threshold:
            kw_result.method = "keywords"
            return kw_result

        self._logger.info(
            "keywords_low_confidence",
            label=kw_result.label,
            confidence=kw_result.confidence,
            threshold=self._cls_config.confidence_threshold,
        )

        if self._models_client is None:
            kw_result.method = "keywords_only_no_llm"
            return kw_result

        llm_result = await self._classify_llm(text, subject, schema_labels)
        return self._merge_results(kw_result, llm_result, prefer="llm")

    async def _llm_first(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_labels: list[dict[str, Any]],
    ) -> ClassificationResult:
        """LLM first, fallback to keyword-based if low confidence."""
        if self._models_client is None:
            return await self._classify_keywords(full_text, schema_labels)

        llm_result = await self._classify_llm(text, subject, schema_labels)

        if llm_result.confidence >= self._cls_config.confidence_threshold:
            llm_result.method = "llm"
            return llm_result

        kw_result = await self._classify_keywords(full_text, schema_labels)
        return self._merge_results(kw_result, llm_result, prefer="keywords")

    async def _ensemble(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_labels: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Run both classifiers and merge with weighted average."""
        kw_result = await self._classify_keywords(full_text, schema_labels)

        if self._models_client is None:
            kw_result.method = "keywords_only_no_llm"
            return kw_result

        llm_result = await self._classify_llm(text, subject, schema_labels)

        # If both agree, boost confidence
        if kw_result.label == llm_result.label:
            combined_confidence = min(
                1.0,
                kw_result.confidence * self._cls_config.sklearn_weight
                + llm_result.confidence * self._cls_config.llm_weight
                + 0.1,  # Agreement bonus
            )
            return ClassificationResult(
                label=kw_result.label,
                display_name=llm_result.display_name or kw_result.display_name,
                confidence=round(combined_confidence, 4),
                sub_label=llm_result.sub_label or kw_result.sub_label,
                method="ensemble_agree",
                sklearn_label=kw_result.label,
                sklearn_confidence=kw_result.confidence,
                llm_label=llm_result.label,
                llm_confidence=llm_result.confidence,
                reasoning=llm_result.reasoning,
            )

        # Disagreement: pick higher weighted confidence
        kw_score = kw_result.confidence * self._cls_config.sklearn_weight
        llm_score = llm_result.confidence * self._cls_config.llm_weight
        prefer = "keywords" if kw_score > llm_score else "llm"
        return self._merge_results(kw_result, llm_result, prefer=prefer)

    # ------------------------------------------------------------------
    # Keyword-based classifier (fast path)
    # ------------------------------------------------------------------

    async def _classify_keywords(
        self,
        text: str,
        schema_labels: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Classify text using keyword matching from schema_labels.

        Uses a TF-IDF-like scoring approach:
        - Count keyword hits per label (case-insensitive, word-boundary aware)
        - Normalize by total keyword count per label
        - Return the label with the highest score

        This is the "fast path" — no ML model, no API call.
        Works purely from the schema_labels keyword lists.
        """
        if not schema_labels:
            return ClassificationResult(
                label="unknown",
                confidence=0.0,
                method="keywords_no_labels",
            )

        text_lower = text.lower()
        scores: dict[str, float] = {}
        label_info: dict[str, dict[str, Any]] = {}

        for label_def in schema_labels:
            label_id = label_def.get("id", "")
            keywords = label_def.get("keywords", [])
            label_info[label_id] = label_def

            if not keywords:
                scores[label_id] = 0.0
                continue

            hit_count = 0
            for kw in keywords:
                kw_lower = kw.lower()
                # Word-boundary aware matching
                pattern = re.compile(r"\b" + re.escape(kw_lower) + r"\b")
                matches = pattern.findall(text_lower)
                hit_count += len(matches)

            # Normalize: hits / total keywords, capped at 1.0
            # Apply log dampening so many hits don't over-inflate
            if hit_count > 0:
                raw_score = hit_count / len(keywords)
                # Log dampening: log(1 + raw_score) / log(2 + raw_score)
                scores[label_id] = math.log(1 + raw_score) / math.log(2 + raw_score)
            else:
                scores[label_id] = 0.0

        if not scores or max(scores.values()) == 0.0:
            return ClassificationResult(
                label="unknown",
                confidence=0.0,
                method="keywords_no_match",
            )

        # Sort by score descending
        sorted_labels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_id, best_score = sorted_labels[0]
        best_info = label_info.get(best_id, {})

        # Build alternatives (top-3 excluding winner)
        alternatives = [
            {"label": lid, "confidence": round(sc, 4)} for lid, sc in sorted_labels[1:4] if sc > 0
        ]

        return ClassificationResult(
            label=best_id,
            display_name=best_info.get("display_name", ""),
            confidence=round(best_score, 4),
            method="keywords",
            sklearn_label=best_id,
            sklearn_confidence=round(best_score, 4),
            alternatives=alternatives,
        )

    # ------------------------------------------------------------------
    # LLM classifier
    # ------------------------------------------------------------------

    async def _classify_llm(
        self,
        text: str,
        subject: str,
        schema_labels: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Classify text using LLM via models_client.generate().

        Builds a classification prompt from schema_labels and parses
        the structured JSON response.
        """
        if self._models_client is None:
            return ClassificationResult(
                label="unknown",
                confidence=0.0,
                method="llm_unavailable",
            )

        # Build label descriptions for the prompt
        label_descriptions = []
        for lbl in schema_labels:
            desc = f"- **{lbl.get('id', '')}** ({lbl.get('display_name', '')}): {lbl.get('description', '')}"
            examples = lbl.get("examples", [])
            if examples:
                example_str = "; ".join(examples[:3])
                desc += f"\n  Examples: {example_str}"
            label_descriptions.append(desc)

        labels_text = "\n".join(label_descriptions)
        valid_ids = [lbl.get("id", "") for lbl in schema_labels]

        system_prompt = (
            "You are a precise text classifier. Classify the given text into "
            "exactly one of the following labels.\n\n"
            f"Available labels:\n{labels_text}\n\n"
            "Return ONLY a JSON object with these fields:\n"
            '  "label": "<one of the label IDs>",\n'
            '  "confidence": <0.0-1.0>,\n'
            '  "reasoning": "<brief explanation>",\n'
            '  "sub_label": "<optional sub-category or null>"\n\n'
            f"Valid label IDs: {json.dumps(valid_ids)}"
        )

        user_content = text
        if subject:
            user_content = f"Subject: {subject}\n\n{text}"

        try:
            result = await self._models_client.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content[:4000]},
                ],
                model=self._cls_config.llm_model,
                temperature=self._cls_config.llm_temperature,
                max_tokens=self._cls_config.max_tokens,
            )

            # Parse JSON response
            response_text = result.output.text.strip()
            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
                response_text = re.sub(r"\s*```$", "", response_text)

            parsed = json.loads(response_text)

            label = parsed.get("label", "unknown")
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = parsed.get("reasoning", "")
            sub_label = parsed.get("sub_label")

            # Look up display_name from schema
            display_name = ""
            for lbl in schema_labels:
                if lbl.get("id") == label:
                    display_name = lbl.get("display_name", "")
                    break

            return ClassificationResult(
                label=label,
                display_name=display_name,
                confidence=round(confidence, 4),
                method="llm",
                sub_label=sub_label,
                reasoning=reasoning,
                llm_label=label,
                llm_confidence=round(confidence, 4),
            )

        except Exception as exc:
            self._logger.error("llm_classify_failed", error=str(exc))
            return ClassificationResult(
                label="unknown",
                confidence=0.0,
                method="llm_error",
            )

    # ------------------------------------------------------------------
    # Result merging
    # ------------------------------------------------------------------

    def _merge_results(
        self,
        kw_result: ClassificationResult,
        llm_result: ClassificationResult,
        prefer: str = "llm",
    ) -> ClassificationResult:
        """Merge keyword-based and LLM results, preferring one source.

        Same logic as HybridClassifier._merge_results from the
        email_intent_processor skill, adapted for generic labels.
        """
        primary = llm_result if prefer == "llm" else kw_result
        secondary = kw_result if prefer == "llm" else llm_result

        return ClassificationResult(
            label=primary.label,
            display_name=primary.display_name or secondary.display_name,
            confidence=round(primary.confidence, 4),
            sub_label=primary.sub_label or secondary.sub_label,
            method=f"hybrid_{prefer}",
            sklearn_label=kw_result.label,
            sklearn_confidence=kw_result.confidence,
            llm_label=llm_result.label,
            llm_confidence=llm_result.confidence,
            alternatives=primary.alternatives or secondary.alternatives,
            reasoning=llm_result.reasoning,
        )
