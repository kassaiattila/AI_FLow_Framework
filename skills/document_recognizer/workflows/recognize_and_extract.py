"""recognize_and_extract — Sprint V SV-1 skeleton; SV-2 fills in.

Pipeline (will be wired in SV-2):

    parse (document_extractor) -> classify (rule engine + LLM fallback)
        -> extract (per-doctype PromptWorkflow descriptor)
        -> intent_routing (safe-eval rules) -> persist (Alembic 048, SV-3)

SV-1 ships only the function signature + a NotImplementedError raise so
that import-time wiring (skill registry, route discovery) succeeds and
SV-2 has a clear seam to fill in.
"""

from __future__ import annotations

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,  # re-exported for skill consumers (see __all__)
    DocIntentDecision,
    DocRecognitionRequest,
    DocTypeMatch,
)

__all__ = ["DocFieldValue", "recognize_and_extract"]


async def recognize_and_extract(
    request: DocRecognitionRequest,
) -> tuple[DocTypeMatch, DocExtractionResult, DocIntentDecision]:
    """SV-1 SKELETON. SV-2 will wire the 3-stage pipeline.

    Returns the triple ``(DocTypeMatch, DocExtractionResult,
    DocIntentDecision)`` per the audit doc design. SV-1 raises
    :class:`NotImplementedError` so callers can import the symbol but a
    concrete invocation surfaces immediately.

    Sprint V SV-2 will replace this body with:

    1. Parser routing via ``document_extractor`` service (docling /
       Azure DI / unstructured) per the descriptor's
       ``parser_preferences``.
    2. Rule-engine classifier with weighted scoring (5 rule kinds).
    3. LLM fallback when ``top1_score < descriptor.type_classifier.llm_threshold_below``.
    4. Per-doctype extraction PromptWorkflow descriptor execution.
    5. Intent routing rule evaluation via ``safe_eval_intent_rule``.
    """
    raise NotImplementedError(
        "recognize_and_extract is a Sprint V SV-1 skeleton. "
        "SV-2 wires the 3-stage pipeline (parse → classify → extract → intent_routing). "
        f"Called with tenant_id={request.tenant_id!r}, "
        f"doc_type_hint={request.doc_type_hint!r}, "
        f"filename={request.filename!r}."
    )
