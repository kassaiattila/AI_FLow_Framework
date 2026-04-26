"""recognize_and_extract — Sprint V SV-2 wires classifier + intent.

Pipeline:

    parse (document_extractor) -> classify (rule engine + LLM fallback)
        -> extract (per-doctype PromptWorkflow descriptor — SV-3)
        -> intent_routing (safe-eval rules) -> persist (Alembic 048, SV-3)

SV-2 ships:
* The skill-level entry function with a real implementation: it wires the
  caller-provided :class:`ClassifierInput` through the
  :class:`DocumentRecognizerOrchestrator` and returns the
  ``(DocTypeMatch, DocExtractionResult, DocIntentDecision)`` triple.
* The extraction step in SV-2 returns an EMPTY ``DocExtractionResult``
  placeholder. SV-3 wires the PromptWorkflowExecutor + cost preflight to
  populate it.
* The orchestrator + registry are constructed lazily on first call so
  unit tests can inject fakes via ``set_orchestrator()``.

Caller responsibility (SV-3 will absorb most of this into the API layer):
1. Run the parser (docling / Azure DI / unstructured) to produce parsed
   text + tables + metadata.
2. Pack into a :class:`ClassifierInput`.
3. Call this function with the request envelope + classifier input.
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,  # re-exported for skill consumers (see __all__)
    DocIntentDecision,
    DocRecognitionRequest,
    DocTypeMatch,
)
from aiflow.services.document_recognizer.classifier import ClassifierInput
from aiflow.services.document_recognizer.orchestrator import (
    DocumentRecognizerOrchestrator,
    LLMClassifyFn,
)
from aiflow.services.document_recognizer.registry import DocTypeRegistry

__all__ = [
    "DocFieldValue",
    "recognize_and_extract",
    "set_orchestrator",
    "get_orchestrator",
]

_DEFAULT_BOOTSTRAP_DIR = Path(__file__).resolve().parents[3] / "data" / "doctypes"
_DEFAULT_TENANT_DIR = Path(__file__).resolve().parents[3] / "data" / "doctypes" / "_tenant"

_lock = RLock()
_orchestrator_instance: DocumentRecognizerOrchestrator | None = None


def _build_default_orchestrator() -> DocumentRecognizerOrchestrator:
    registry = DocTypeRegistry(
        bootstrap_dir=_DEFAULT_BOOTSTRAP_DIR,
        tenant_overrides_dir=_DEFAULT_TENANT_DIR,
    )
    # SV-2 ships without an LLM fallback wired in by default; SV-3 wires it
    # up against the ClassifierService once the API layer is present.
    return DocumentRecognizerOrchestrator(registry=registry, llm_classify_fn=None)


def get_orchestrator() -> DocumentRecognizerOrchestrator:
    """Module-level singleton; tests can swap via :func:`set_orchestrator`."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        with _lock:
            if _orchestrator_instance is None:
                _orchestrator_instance = _build_default_orchestrator()
    return _orchestrator_instance


def set_orchestrator(orchestrator: DocumentRecognizerOrchestrator | None) -> None:
    """Inject a fake orchestrator (tests). Pass ``None`` to reset to default."""
    global _orchestrator_instance
    with _lock:
        _orchestrator_instance = orchestrator


async def recognize_and_extract(
    request: DocRecognitionRequest,
    classifier_input: ClassifierInput,
    *,
    pii_detected: bool = False,
    llm_classify_fn: LLMClassifyFn | None = None,
) -> tuple[DocTypeMatch, DocExtractionResult, DocIntentDecision] | None:
    """SV-2 — classify + intent routing. Extraction is a SV-3 placeholder.

    Returns ``None`` when no doc-type matched and no LLM fallback could
    rescue the classification. Operators can interpret ``None`` as "send
    to manual review" (the API layer in SV-3 will translate it to a
    ``DocIntentDecision(intent='route_to_human', reason='no match')``).

    :param request: input envelope (tenant_id + optional doc_type_hint).
    :param classifier_input: parsed-document signals built by the caller
        from a :mod:`aiflow.services.document_extractor` parse result.
    :param pii_detected: orchestrator-supplied flag forwarded to the
        intent routing rule evaluator.
    :param llm_classify_fn: optional per-call LLM fallback override —
        when supplied, replaces the orchestrator's default ``None`` for
        this call only (SV-2 doesn't yet wire a default LLM).
    """
    orchestrator = get_orchestrator()

    # Per-call LLM fallback override: re-bind the orchestrator's callable
    # for this call without mutating the singleton.
    if llm_classify_fn is not None:
        # Build a temporary orchestrator that shares the registry but uses
        # the per-call LLM fn. Cheap (no I/O); preserves cache.
        temp = DocumentRecognizerOrchestrator(
            registry=orchestrator._registry,  # noqa: SLF001 — internal access OK in same package
            llm_classify_fn=llm_classify_fn,
        )
        return await temp.run(
            classifier_input,
            tenant_id=request.tenant_id,
            doc_type_hint=request.doc_type_hint,
            pii_detected=pii_detected,
        )

    return await orchestrator.run(
        classifier_input,
        tenant_id=request.tenant_id,
        doc_type_hint=request.doc_type_hint,
        pii_detected=pii_detected,
    )
