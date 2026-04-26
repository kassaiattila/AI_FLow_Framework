"""DocumentRecognizer orchestrator — Sprint V SV-2.

Wires the 3-stage pipeline that the SV-1 ``recognize_and_extract`` skeleton
left as ``NotImplementedError``:

    parse (caller-provided ClassifierInput) -> classify (rule engine + LLM
        fallback) -> resolve extraction PromptWorkflow descriptor ->
        intent_routing (safe-eval rules) -> assemble result triple.

SV-2 keeps the orchestrator **LLM-free for the classifier path** when the
rule engine produces a confident match. When ``needs_llm_fallback`` returns
True, the orchestrator delegates to the caller-supplied
``llm_classify_fn`` (typically the ``ClassifierService.classify``-style
callable from Sprint K UC3). When ``llm_classify_fn`` is None the
orchestrator returns the rule-engine match unchanged (degraded mode).

The actual extraction step is **deferred to SV-3** — SV-2 returns an
empty ``DocExtractionResult`` placeholder so SV-3 can wire in the
PromptWorkflowExecutor + cost preflight without touching the SV-2 surface.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocIntentDecision,
    DocTypeDescriptor,
    DocTypeMatch,
)
from aiflow.services.document_recognizer.classifier import (
    ClassifierInput,
    classify_doctype,
    needs_llm_fallback,
)
from aiflow.services.document_recognizer.registry import DocTypeRegistry
from aiflow.services.document_recognizer.safe_eval import (
    SafeEvalError,
    safe_eval_intent_rule,
)

__all__ = [
    "DocumentRecognizerOrchestrator",
    "LLMClassifyFn",
]

logger = structlog.get_logger(__name__)


# Type alias for the (optional) LLM fallback callable.
# Receives top-k descriptors + ctx text, returns (doc_type_name, confidence).
LLMClassifyFn = Callable[
    [list[DocTypeDescriptor], ClassifierInput],
    Awaitable[tuple[str, float] | None],
]


class DocumentRecognizerOrchestrator:
    """Stateful coordinator. Reuses a :class:`DocTypeRegistry` across calls."""

    def __init__(
        self,
        registry: DocTypeRegistry,
        llm_classify_fn: LLMClassifyFn | None = None,
    ) -> None:
        self._registry = registry
        self._llm_classify_fn = llm_classify_fn

    async def classify(
        self,
        ctx: ClassifierInput,
        *,
        tenant_id: str,
        doc_type_hint: str | None = None,
    ) -> tuple[DocTypeMatch | None, DocTypeDescriptor | None]:
        """Stage 1+2 — classify and resolve descriptor.

        Returns ``(match, descriptor)`` or ``(None, None)`` if no rule matched
        and the LLM fallback is unavailable / off / also returns nothing.
        """
        # Operator-supplied hint short-circuits the rule engine when the hint
        # matches a known descriptor in the tenant view.
        if doc_type_hint:
            descriptor = self._registry.get_doctype(doc_type_hint, tenant_id=tenant_id)
            if descriptor is not None:
                logger.debug(
                    "doc_recognizer.hint_used",
                    tenant_id=tenant_id,
                    doc_type=doc_type_hint,
                )
                # Synthesize a high-confidence match — the operator told us.
                return (
                    DocTypeMatch(doc_type=doc_type_hint, confidence=1.0, alternatives=[]),
                    descriptor,
                )

        descriptors = self._registry.list_doctypes(tenant_id=tenant_id)
        if not descriptors:
            logger.warning("doc_recognizer.empty_registry", tenant_id=tenant_id)
            return None, None

        match = classify_doctype(descriptors, ctx)
        primary_descriptor: DocTypeDescriptor | None = None
        if match is not None:
            primary_descriptor = self._registry.get_doctype(match.doc_type, tenant_id=tenant_id)

        if needs_llm_fallback(match, primary_descriptor) and self._llm_classify_fn is not None:
            logger.info(
                "doc_recognizer.llm_fallback_invoked",
                tenant_id=tenant_id,
                rule_score=match.confidence if match else 0.0,
            )
            try:
                llm_result = await self._llm_classify_fn(descriptors, ctx)
            except Exception as exc:  # noqa: BLE001 — LLM never crashes the recognizer
                logger.warning("doc_recognizer.llm_fallback_error", error=str(exc)[:200])
                llm_result = None

            if llm_result is not None:
                llm_doc_type, llm_confidence = llm_result
                llm_descriptor = self._registry.get_doctype(llm_doc_type, tenant_id=tenant_id)
                if llm_descriptor is not None and llm_confidence > (
                    match.confidence if match else 0.0
                ):
                    # LLM beat the rule engine — replace the primary match.
                    alternatives = []
                    if match is not None:
                        alternatives = [(match.doc_type, match.confidence)]
                    match = DocTypeMatch(
                        doc_type=llm_doc_type,
                        confidence=float(llm_confidence),
                        alternatives=alternatives,
                    )
                    primary_descriptor = llm_descriptor

        return match, primary_descriptor

    def route_intent(
        self,
        descriptor: DocTypeDescriptor,
        extraction: DocExtractionResult,
        match: DocTypeMatch,
        *,
        pii_detected: bool = False,
    ) -> DocIntentDecision:
        """Stage 4 — evaluate intent routing rules in declared order.

        First rule whose ``if_expr`` evaluates truthy wins. If no rule fires,
        return the descriptor's ``default`` intent.
        """
        for rule in descriptor.intent_routing.conditions:
            try:
                fired = safe_eval_intent_rule(
                    rule.if_expr,
                    extraction.extracted_fields,
                    doc_type_confidence=match.confidence,
                    pii_detected=pii_detected,
                )
            except SafeEvalError as exc:
                logger.warning(
                    "doc_recognizer.intent_rule_eval_error",
                    descriptor=descriptor.name,
                    if_expr=rule.if_expr,
                    error=str(exc)[:200],
                )
                continue
            if fired:
                logger.debug(
                    "doc_recognizer.intent_rule_fired",
                    descriptor=descriptor.name,
                    if_expr=rule.if_expr,
                    intent=rule.intent,
                )
                return DocIntentDecision(intent=rule.intent, reason=rule.reason)

        # Default: descriptor.intent_routing.default.
        return DocIntentDecision(
            intent=descriptor.intent_routing.default,
            reason="default",
        )

    async def run(
        self,
        ctx: ClassifierInput,
        *,
        tenant_id: str,
        doc_type_hint: str | None = None,
        pii_detected: bool = False,
    ) -> tuple[DocTypeMatch, DocExtractionResult, DocIntentDecision] | None:
        """End-to-end orchestration. Returns ``None`` if classification fails.

        SV-2 stops at the classifier + intent stages — the extraction step
        returns an EMPTY ``DocExtractionResult`` (no fields). SV-3 wires
        the PromptWorkflowExecutor + cost preflight to populate it.
        """
        match, descriptor = await self.classify(
            ctx, tenant_id=tenant_id, doc_type_hint=doc_type_hint
        )
        if match is None or descriptor is None:
            return None

        # SV-2 placeholder: empty extraction. SV-3 fills this in.
        extraction = DocExtractionResult(
            doc_type=match.doc_type,
            extracted_fields={},
            validation_warnings=[],
            cost_usd=0.0,
            extraction_time_ms=0.0,
        )

        intent = self.route_intent(
            descriptor,
            extraction,
            match,
            pii_detected=pii_detected,
        )
        return match, extraction, intent

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_audit_payload(
        self,
        match: DocTypeMatch,
        extraction: DocExtractionResult,
        intent: DocIntentDecision,
        *,
        tenant_id: str,
        pii_redaction: bool = False,
    ) -> dict[str, Any]:
        """Build the JSONB payload the SV-3 audit-log boundary will write.

        When ``pii_redaction`` is True (driven by the descriptor's
        ``intent_routing.pii_redaction`` flag), every field VALUE is
        replaced with the literal string ``"<redacted>"``. Field NAMES +
        confidences + extraction metadata stay intact for forensic /
        observability use.
        """
        fields_payload: dict[str, Any] = {}
        for name, fv in extraction.extracted_fields.items():
            value = "<redacted>" if pii_redaction else fv.value
            fields_payload[name] = {
                "value": value,
                "confidence": fv.confidence,
            }
        return {
            "tenant_id": tenant_id,
            "doc_type": match.doc_type,
            "doc_type_confidence": match.confidence,
            "alternatives": [list(a) for a in match.alternatives],
            "extracted_fields": fields_payload,
            "validation_warnings": list(extraction.validation_warnings),
            "intent": intent.intent,
            "intent_reason": intent.reason,
            "cost_usd": extraction.cost_usd,
            "extraction_time_ms": extraction.extraction_time_ms,
            "pii_redacted": pii_redaction,
        }
