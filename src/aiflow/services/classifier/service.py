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
    "EXTRACT_INTENT_IDS",
]

# Sprint O / S128 — Sprint K v1 schema labels considered "EXTRACT-class".
# Source: data/fixtures/emails_sprint_o/manifest.yaml
# (categories.EXTRACT.sprint_k_intents). Hard-coded for now because the
# schema has no native ``intent_class`` field; revisit when the schema gains
# one.
EXTRACT_INTENT_IDS: frozenset[str] = frozenset({"invoice_received", "order"})

# Confidence ceiling for the attachment-feature rule boost. Plan §4 LEPES 3.
_RULE_BOOST_DELTA = 0.3
_RULE_BOOST_CAP = 0.95
_RULE_BOOST_BODY_THRESHOLD = 0.6

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
        context: dict[str, Any] | None = None,
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
            context: Optional structured context (Sprint O / S128). Recognised
                keys:

                - ``attachment_features`` — dict from
                  :class:`AttachmentFeatures.model_dump`; triggers the rule
                  boost when body confidence is below
                  ``_RULE_BOOST_BODY_THRESHOLD``.
                - ``attachment_text_preview`` — first ~500 chars of attachment
                  text; appended to the LLM prompt when the caller opts into
                  the LLM-context path.
                - ``attachment_intent_llm_context`` — bool; when True the
                  :meth:`_classify_llm` path injects the second system
                  message. Defaults to False to preserve Sprint K cost.

        Returns:
            ClassificationResult with the winning label and metadata.
        """
        active_strategy = (
            ClassificationStrategy(strategy) if strategy else self._cls_config.strategy
        )
        labels = schema_labels or []
        full_text = f"{subject}\n\n{text}" if subject else text

        if active_strategy == ClassificationStrategy.SKLEARN_ONLY:
            base = await self._classify_keywords(full_text, labels)
        elif active_strategy == ClassificationStrategy.LLM_ONLY:
            base = await self._classify_llm(text, subject, labels, context=context)
        elif active_strategy == ClassificationStrategy.SKLEARN_FIRST:
            base = await self._keywords_first(text, subject, full_text, labels, context=context)
        elif active_strategy == ClassificationStrategy.LLM_FIRST:
            base = await self._llm_first(text, subject, full_text, labels, context=context)
        elif active_strategy == ClassificationStrategy.ENSEMBLE:
            base = await self._ensemble(text, subject, full_text, labels, context=context)
        else:
            self._logger.warning("unknown_strategy", strategy=active_strategy)
            base = await self._keywords_first(text, subject, full_text, labels, context=context)

        # Sprint O / S128 — attachment-feature rule boost. Pure post-process,
        # only fires when ``context["attachment_features"]`` carries one of
        # the booleans and the body-derived confidence is below threshold.
        return _apply_attachment_rule_boost(base, labels, context)

    # ------------------------------------------------------------------
    # Strategy orchestrators
    # ------------------------------------------------------------------

    async def _keywords_first(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_labels: list[dict[str, Any]],
        *,
        context: dict[str, Any] | None = None,
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

        llm_result = await self._classify_llm(text, subject, schema_labels, context=context)
        return self._merge_results(kw_result, llm_result, prefer="llm")

    async def _llm_first(
        self,
        text: str,
        subject: str,
        full_text: str,
        schema_labels: list[dict[str, Any]],
        *,
        context: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """LLM first, fallback to keyword-based if low confidence."""
        if self._models_client is None:
            return await self._classify_keywords(full_text, schema_labels)

        llm_result = await self._classify_llm(text, subject, schema_labels, context=context)

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
        *,
        context: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """Run both classifiers and merge with weighted average."""
        kw_result = await self._classify_keywords(full_text, schema_labels)

        if self._models_client is None:
            kw_result.method = "keywords_only_no_llm"
            return kw_result

        llm_result = await self._classify_llm(text, subject, schema_labels, context=context)

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
        *,
        context: dict[str, Any] | None = None,
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

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        attachment_message = _build_attachment_context_message(context)
        if attachment_message is not None:
            messages.append({"role": "system", "content": attachment_message})
        messages.append({"role": "user", "content": user_content[:4000]})

        try:
            result = await self._models_client.generate(
                messages=messages,
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


# ---------------------------------------------------------------------------
# Sprint O / S128 — attachment-feature rule boost + LLM-context helpers
# ---------------------------------------------------------------------------


def _build_attachment_context_message(context: dict[str, Any] | None) -> str | None:
    """Render the LLM-context system message, or ``None`` if the caller did
    not opt in.

    Activated only when ``context["attachment_intent_llm_context"]`` is True
    (orchestrator threads this from
    :class:`UC3AttachmentIntentSettings.llm_context`). Keeps the LLM cost
    profile unchanged for Sprint K callers and the default Sprint O ON path.
    """
    if not context:
        return None
    if not context.get("attachment_intent_llm_context"):
        return None
    features = context.get("attachment_features") or {}
    preview = (context.get("attachment_text_preview") or "")[:500]

    lines: list[str] = ["Additional attachment context (Sprint O):"]
    lines.append(
        "- invoice_number_detected="
        f"{bool(features.get('invoice_number_detected'))}"
        f"; total_value_detected={bool(features.get('total_value_detected'))}"
    )
    lines.append(f"- mime_profile={features.get('mime_profile', 'none')!r}")
    buckets = features.get("keyword_buckets") or {}
    if buckets:
        top = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)[:3]
        bucket_str = ", ".join(f"{name}={count}" for name, count in top)
        lines.append(f"- keyword_buckets (top 3): {bucket_str}")
    if preview:
        lines.append("- attachment_text_preview (truncated to 500 chars):")
        lines.append(preview)
    return "\n".join(lines)


def _apply_attachment_rule_boost(
    base: ClassificationResult,
    schema_labels: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> ClassificationResult:
    """Boost the closest EXTRACT-class label when attachment signals fire.

    Plan §4 LEPES 3 (refined after S128 first-pass measurement):
        body confidence < 0.6
        AND body label is in {"unknown"} ∪ EXTRACT_INTENT_IDS  ← gate
        AND attachment carries an EXTRACT signal
        → boost the *signal-aligned* EXTRACT label by +0.3 (cap 0.95).

    The body-label gate prevents the boost from clobbering correctly
    identified non-EXTRACT intents (complaint, support, marketing,
    inquiry, …) when a low-confidence keyword score happens to slip
    under the 0.6 floor. Signal-aligned label selection avoids the
    "always picks `order`" bug from naive alternatives-based selection.

    Signal alignment:

    - ``invoice_number_detected`` → ``invoice_received`` (HU/EN INV regex
      is the strongest evidence for a delivered invoice).
    - ``keyword_buckets["contract"] > 0`` and no invoice number →
      ``order`` (Sprint K v1 schema groups contract intents under
      ``order``).
    - ``total_value_detected`` only → ``invoice_received`` (payment-due
      lines are statistically much more often invoices than contracts in
      our fixture corpus).
    """
    if not context:
        return base
    features = context.get("attachment_features")
    if not features:
        return base
    if base.confidence >= _RULE_BOOST_BODY_THRESHOLD:
        return base
    if base.label not in EXTRACT_INTENT_IDS and base.label != "unknown":
        return base

    invoice_hit = bool(features.get("invoice_number_detected"))
    total_hit = bool(features.get("total_value_detected"))
    contract_hit = int((features.get("keyword_buckets") or {}).get("contract", 0)) > 0
    if not (invoice_hit or total_hit or contract_hit):
        return base

    # Pick EXTRACT label aligned with the strongest signal.
    if invoice_hit:
        preferred_id = "invoice_received"
    elif contract_hit:
        preferred_id = "order"
    else:  # total_hit only
        preferred_id = "invoice_received"

    chosen: dict[str, Any] | None = next(
        (lbl for lbl in schema_labels if lbl.get("id") == preferred_id), None
    )
    if chosen is None:
        # Fall back to the first EXTRACT label present in the schema.
        chosen = next((lbl for lbl in schema_labels if lbl.get("id") in EXTRACT_INTENT_IDS), None)
    if chosen is None:
        return base

    chosen_id = chosen.get("id", "")
    alt_scores: dict[str, float] = {
        alt.get("label", ""): float(alt.get("confidence", 0.0)) for alt in base.alternatives
    }
    base_confidence_for_chosen = alt_scores.get(
        chosen_id, base.confidence if base.label == chosen_id else 0.0
    )
    boosted = min(
        _RULE_BOOST_CAP, max(base_confidence_for_chosen, base.confidence) + _RULE_BOOST_DELTA
    )

    fired: list[str] = []
    if invoice_hit:
        fired.append("invoice_number_detected")
    if total_hit:
        fired.append("total_value_detected")
    if contract_hit:
        fired.append("contract_keyword_bucket")
    fired_str = "+".join(fired)
    reasoning_prefix = (
        f"Attachment rule boost: {fired_str} → boosted '{chosen_id}' "
        f"by +{_RULE_BOOST_DELTA} (cap {_RULE_BOOST_CAP}). "
    )

    return ClassificationResult(
        label=chosen_id,
        display_name=chosen.get("display_name", base.display_name),
        confidence=round(boosted, 4),
        method=f"{base.method}+attachment_rule" if base.method else "attachment_rule",
        sub_label=base.sub_label,
        alternatives=base.alternatives,
        reasoning=reasoning_prefix + (base.reasoning or ""),
        sklearn_label=base.sklearn_label,
        sklearn_confidence=base.sklearn_confidence,
        llm_label=base.llm_label,
        llm_confidence=base.llm_confidence,
    )
