"""DocumentRecognizer orchestrator — Sprint V SV-2 + Sprint W SW-1.

Wires the 4-stage pipeline:

    parse (caller-provided ClassifierInput) -> classify (rule engine + LLM
        fallback) -> extract (Sprint W SW-1: real PromptWorkflow execution
        with per-step cost preflight + field validators) -> intent_routing
        (safe-eval rules) -> assemble result triple.

Sprint V SV-2 shipped stages 1+2+4 with an EMPTY extraction placeholder.
Sprint W SW-1 fills the extraction stage in: when an ``extract_fn`` is
injected, the orchestrator resolves the descriptor's
``extraction.workflow`` PromptWorkflow descriptor + invokes per-step LLM
calls + maps results into ``DocFieldValue`` entries. Without an
``extract_fn`` the orchestrator preserves the SV-2 placeholder behavior
(empty extraction; downstream tests that don't need extraction still
work).

LLM fallback for classifier (SV-2): graceful degradation on None /
exception — rule-engine match preserved.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,
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
from aiflow.services.document_recognizer.validators import apply_validators

__all__ = [
    "DocumentRecognizerOrchestrator",
    "ExtractFn",
    "LLMClassifyFn",
]

logger = structlog.get_logger(__name__)


# Type alias for the (optional) LLM fallback callable.
# Receives top-k descriptors + ctx text, returns (doc_type_name, confidence).
LLMClassifyFn = Callable[
    [list[DocTypeDescriptor], ClassifierInput],
    Awaitable[tuple[str, float] | None],
]

# Sprint W SW-1 — extraction stage callable. Receives the descriptor +
# parsed text + tenant_id; returns a populated DocExtractionResult (or
# raises CostGuardrailRefused if a per-step ceiling fires). Contract is
# async so the implementation can do real LLM calls; deterministic fakes
# in tests just return a coroutine.
ExtractFn = Callable[
    [DocTypeDescriptor, ClassifierInput, str],
    Awaitable[DocExtractionResult],
]


class DocumentRecognizerOrchestrator:
    """Stateful coordinator. Reuses a :class:`DocTypeRegistry` across calls."""

    def __init__(
        self,
        registry: DocTypeRegistry,
        llm_classify_fn: LLMClassifyFn | None = None,
        extract_fn: ExtractFn | None = None,
    ) -> None:
        self._registry = registry
        self._llm_classify_fn = llm_classify_fn
        self._extract_fn = extract_fn

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

        Sprint W SW-1: when an ``extract_fn`` was injected at construction,
        the orchestrator delegates to it. Otherwise (no ``extract_fn``)
        the SV-2 placeholder behavior is preserved — empty extraction +
        validation_warnings note explaining why. Field validators run on
        the extracted values regardless of source (real LLM or fake).
        """
        match, descriptor = await self.classify(
            ctx, tenant_id=tenant_id, doc_type_hint=doc_type_hint
        )
        if match is None or descriptor is None:
            return None

        extraction = await self._extract(ctx, descriptor, tenant_id=tenant_id)

        intent = self.route_intent(
            descriptor,
            extraction,
            match,
            pii_detected=pii_detected,
        )
        return match, extraction, intent

    async def _extract(
        self,
        ctx: ClassifierInput,
        descriptor: DocTypeDescriptor,
        *,
        tenant_id: str,
    ) -> DocExtractionResult:
        """Stage 3 — extraction. Sprint W SW-1.

        When ``self._extract_fn`` is set, delegate; otherwise return an
        empty placeholder with a validation_warning explaining the gap.
        Field validators (``apply_validators``) run on the result so even
        fake / placeholder extractions get a consistent warning surface.
        """
        if self._extract_fn is None:
            logger.info(
                "doc_recognizer.extract_skipped",
                doc_type=descriptor.name,
                reason="no_extract_fn",
            )
            return DocExtractionResult(
                doc_type=descriptor.name,
                extracted_fields={},
                validation_warnings=[
                    "extract_fn not configured — extraction skipped (Sprint V SV-2 placeholder)"
                ],
                cost_usd=0.0,
                extraction_time_ms=0.0,
            )

        start = time.monotonic()
        try:
            result = await self._extract_fn(descriptor, ctx, tenant_id)
        except Exception:
            # Re-raise — CostGuardrailRefused / network / parse errors
            # surface to the caller for explicit handling.
            raise

        # Sprint W SW-1: re-run field validators on the result. The
        # extract_fn implementation may have already produced warnings;
        # we ADD validator-driven warnings without dropping the originals.
        validator_warnings = self._validate_fields(descriptor, result.extracted_fields)
        if validator_warnings:
            merged_warnings = list(result.validation_warnings) + validator_warnings
            result = result.model_copy(update={"validation_warnings": merged_warnings})

        # Stamp extraction_time_ms if the extract_fn didn't.
        if result.extraction_time_ms <= 0.0:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            result = result.model_copy(update={"extraction_time_ms": elapsed_ms})

        return result

    @staticmethod
    def _validate_fields(
        descriptor: DocTypeDescriptor,
        extracted_fields: dict[str, DocFieldValue],
    ) -> list[str]:
        """Apply field-level validators per the descriptor's extraction.fields list.

        Returns a flat list of warning strings (qualified by field name).
        Missing required fields also get a warning. Never raises.
        """
        warnings: list[str] = []
        for field_spec in descriptor.extraction.fields:
            fv = extracted_fields.get(field_spec.name)
            if fv is None:
                if field_spec.required:
                    warnings.append(f"{field_spec.name}: required but not extracted")
                continue
            field_warnings = apply_validators(fv.value, field_spec.validators)
            warnings.extend(f"{field_spec.name}: {w}" for w in field_warnings)
        return warnings

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
