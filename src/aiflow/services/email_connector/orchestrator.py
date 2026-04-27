"""Scan-classify orchestrator — EmailSource → IntakePackageSink → ClassifierService.

Thin composition layer for UC3 Sprint K. Fetches one package at a time from the
source adapter, persists it through the sink, classifies the package's
EMAIL_BODY description, optionally applies an :class:`IntentRoutingPolicy` to
pick a downstream action, and records the outcome in ``workflow_runs`` via
:class:`StateRepository`.

No new table, no new migration, no new pipeline step — reuses existing
``workflow_runs.output_data`` JSONB column for classification persistence and
adds the routing decision as extra keys in that JSON (``routing_action``,
``routing_target``).

S106 added scan-classify. S107 adds per-tenant intent routing + optional
Langfuse prompt fetch (fetch-only breadcrumb; prompt → schema_labels parsing
is deferred to S108).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from aiflow.intake.package import DescriptionRole

if TYPE_CHECKING:
    from aiflow.contracts.uc3_routing import ExtractionOutcome, ExtractionPath
    from aiflow.core.config import (
        UC3AttachmentIntentSettings,
        UC3DocRecognizerRoutingSettings,
        UC3ExtractionSettings,
    )
    from aiflow.guardrails.cost_preflight import CostPreflightGuardrail
    from aiflow.intake.package import IntakeFile, IntakePackage
    from aiflow.policy.intent_routing import IntentRoutingPolicy
    from aiflow.prompts.manager import PromptManager
    from aiflow.services.classifier.service import (
        ClassificationResult,
        ClassifierService,
    )
    from aiflow.services.document_recognizer.classifier import ClassifierInput
    from aiflow.services.document_recognizer.orchestrator import (
        DocumentRecognizerOrchestrator,
    )
    from aiflow.sources.base import SourceAdapter
    from aiflow.sources.sink import IntakePackageSink
    from aiflow.state.repository import StateRepository
    from aiflow.tools.attachment_processor import ProcessedAttachment

# Runtime references — keep these visible to ruff so the autoformatter
# doesn't strip them as unused on subsequent edits.
_RUNTIME_HOOKS = (asyncio, Path)

__all__ = [
    "_route_extract_by_doctype",
    "build_default_doc_recognizer_orchestrator",
    "scan_and_classify",
]

logger = structlog.get_logger(__name__)

WORKFLOW_NAME = "email_connector_scan_classify"
WORKFLOW_VERSION = "1.0"
SKILL_NAME = "email_intent_processor"


async def scan_and_classify(
    adapter: SourceAdapter,
    sink: IntakePackageSink,
    classifier: ClassifierService,
    repo: StateRepository,
    *,
    tenant_id: str,
    max_items: int = 10,
    schema_labels: list[dict[str, Any]] | None = None,
    routing_policy: IntentRoutingPolicy | None = None,
    prompt_manager: PromptManager | None = None,
    prompt_name: str = "",
    prompt_label: str = "prod",
    attachment_intent_settings: UC3AttachmentIntentSettings | None = None,
    extraction_settings: UC3ExtractionSettings | None = None,
    routing_settings: UC3DocRecognizerRoutingSettings | None = None,
    doc_recognizer_orchestrator: DocumentRecognizerOrchestrator | None = None,
    cost_preflight: CostPreflightGuardrail | None = None,
) -> list[tuple[str, ClassificationResult]]:
    """Drain up to ``max_items`` packages: fetch → sink → classify → (route) → persist.

    Per package:
        1. ``adapter.fetch_next()``  (idle → break)
        2. ``sink.handle(pkg)``       (associate + persist IntakePackage)
        3. ``classifier.classify(text, schema_labels=...)``
        4. If ``routing_policy`` is provided:
           ``routing_policy.decide(result.label, result.confidence)`` →
           ``(action, target)``, persisted as ``output_data.routing_action`` /
           ``output_data.routing_target`` and emitted as a
           ``email_connector.scan_and_classify.routed`` structlog event.
        5. ``repo.create_workflow_run`` + ``repo.update_workflow_run_status``
        6. ``adapter.acknowledge(pkg.package_id)``

    Langfuse prompt fetch: when both ``prompt_manager`` and ``prompt_name`` are
    provided, the orchestrator tries to resolve the prompt once (before the
    drain loop) via :meth:`PromptManager.get` with ``prompt_label``. Successful
    resolution is recorded as ``prompt_version`` in each ``output_data`` (and
    emitted as a ``email_connector.scan_and_classify.prompt_fetched`` event).
    Failures fall through silently; the explicit ``schema_labels`` parameter
    remains authoritative. Extracting ``schema_labels`` from the fetched
    prompt is deferred to S108 (PromptConfig has no native labels field).

    Returns a list of ``(package_id, ClassificationResult)`` for processed
    packages. Packages with no classifiable text are sink-persisted and acked
    but do not produce a ClassificationResult.
    """
    results: list[tuple[str, ClassificationResult]] = []

    prompt_version: str = ""
    if prompt_manager is not None and prompt_name:
        try:
            fetched = prompt_manager.get(prompt_name, label=prompt_label)
            prompt_version = fetched.version or ""
            logger.info(
                "email_connector.scan_and_classify.prompt_fetched",
                tenant_id=tenant_id,
                prompt_name=prompt_name,
                prompt_label=prompt_label,
                prompt_version=prompt_version,
            )
        except Exception as exc:
            logger.info(
                "email_connector.scan_and_classify.prompt_fetch_skipped",
                tenant_id=tenant_id,
                prompt_name=prompt_name,
                prompt_label=prompt_label,
                reason=str(exc),
            )

    for _ in range(max_items):
        package = await adapter.fetch_next()
        if package is None:
            break

        await sink.handle(package)

        text = _extract_classifiable_text(package)
        if not text:
            await adapter.acknowledge(package.package_id)
            logger.info(
                "email_connector.scan_and_classify.empty_package_skipped",
                tenant_id=tenant_id,
                package_id=str(package.package_id),
            )
            continue

        run = await repo.create_workflow_run(
            workflow_name=WORKFLOW_NAME,
            workflow_version=WORKFLOW_VERSION,
            input_data={
                "package_id": str(package.package_id),
                "tenant_id": tenant_id,
                "source_type": package.source_type.value,
                "text_length": len(text),
            },
            skill_name=SKILL_NAME,
        )

        # UC3 Sprint O — extract attachment features BEFORE classification
        # so the rule boost (S128) can flow through ClassifierService.classify
        # via the ``context`` kwarg. Flag-OFF contract: zero new behaviour
        # (no AttachmentProcessor instantiation, no extra log events, no new
        # keys in output_data, no context passed to classify()).
        attachment_payload: dict[str, Any] | None = None
        classifier_context: dict[str, Any] | None = None
        if (
            attachment_intent_settings is not None
            and attachment_intent_settings.enabled
            and package.files
        ):
            attachment_payload = await _maybe_extract_attachment_features(
                package.files,
                settings=attachment_intent_settings,
                workflow_run_id=str(run.id),
            )
            if attachment_payload is not None:
                features = attachment_payload.get("attachment_features")
                preview = attachment_payload.get("attachment_text_preview", "")
                classifier_context = {
                    "attachment_features": features,
                    "attachment_text_preview": preview,
                    "attachment_intent_llm_context": attachment_intent_settings.llm_context,
                }
                logger.info(
                    "email_connector.scan_and_classify.attachment_features_extracted",
                    tenant_id=tenant_id,
                    package_id=str(package.package_id),
                    workflow_run_id=str(run.id),
                    invoice_number_detected=(features or {}).get("invoice_number_detected", False),
                    total_value_detected=(features or {}).get("total_value_detected", False),
                    mime_profile=(features or {}).get("mime_profile", "none"),
                    attachments_considered=(features or {}).get("attachments_considered", 0),
                )

        # S132 — when the attachment-intent flag is on, let the operator
        # pick the classifier strategy (default SKLEARN_FIRST — see plan
        # 113 §3). Flag-off callers stick with the service's configured
        # default so Sprint K behaviour is unchanged.
        strategy_override: str | None = None
        if (
            attachment_intent_settings is not None
            and attachment_intent_settings.enabled
            and attachment_intent_settings.classifier_strategy
        ):
            strategy_override = attachment_intent_settings.classifier_strategy

        result = await classifier.classify(
            text=text,
            schema_labels=schema_labels,
            context=classifier_context,
            strategy=strategy_override,
        )

        output_data: dict[str, Any] = {
            "package_id": str(package.package_id),
            "tenant_id": tenant_id,
            "label": result.label,
            "display_name": result.display_name,
            "confidence": result.confidence,
            "method": result.method,
            "sub_label": result.sub_label,
            "reasoning": result.reasoning,
        }
        if prompt_version:
            output_data["prompt_name"] = prompt_name
            output_data["prompt_version"] = prompt_version
        if attachment_payload is not None and attachment_payload.get("attachment_features"):
            output_data["attachment_features"] = attachment_payload["attachment_features"]

        # Sprint Q / S135 — invoice_processor extraction when the classifier
        # outputs intent_class == "EXTRACT" AND the caller opted in via
        # UC3ExtractionSettings. Flag-off contract: no import, no log event,
        # no new keys in output_data.
        #
        # Sprint X / SX-2 — when ``routing_settings`` is also enabled, the
        # extract path is wrapped by ``_route_extract_by_doctype`` which
        # classifies each attachment with DocRecognizer first and dispatches
        # by detected doctype (``hu_invoice`` → invoice_processor byte-stable;
        # other doctypes → DocRecognizer's PromptWorkflow extraction).
        # Flag-off (default) preserves the Sprint Q path bit-for-bit.
        if (
            extraction_settings is not None
            and extraction_settings.enabled
            and package.files
            and _intent_class_is_extract(result)
        ):
            if routing_settings is not None and routing_settings.enabled:
                routing_payload = await _route_extract_by_doctype(
                    package.files,
                    routing_settings=routing_settings,
                    extraction_settings=extraction_settings,
                    tenant_id=tenant_id,
                    workflow_run_id=str(run.id),
                    doc_recognizer_orchestrator=doc_recognizer_orchestrator,
                    cost_preflight=cost_preflight,
                )
                if routing_payload is not None:
                    output_data["extracted_fields"] = routing_payload["extracted_fields"]
                    output_data["routing_decision"] = routing_payload["routing_decision"]
                    logger.info(
                        "email_connector.scan_and_classify.extracted_fields_persisted",
                        tenant_id=tenant_id,
                        package_id=str(package.package_id),
                        workflow_run_id=str(run.id),
                        file_count=len(routing_payload["extracted_fields"]),
                        total_cost_usd=routing_payload.get("total_cost_usd", 0.0),
                        routing_enabled=True,
                    )
            else:
                extraction_payload = await _maybe_extract_invoice_fields(
                    package.files,
                    settings=extraction_settings,
                    workflow_run_id=str(run.id),
                )
                if extraction_payload is not None:
                    output_data["extracted_fields"] = extraction_payload["extracted_fields"]
                    logger.info(
                        "email_connector.scan_and_classify.extracted_fields_persisted",
                        tenant_id=tenant_id,
                        package_id=str(package.package_id),
                        workflow_run_id=str(run.id),
                        file_count=len(extraction_payload["extracted_fields"]),
                        total_cost_usd=extraction_payload.get("total_cost_usd", 0.0),
                    )

        if routing_policy is not None:
            action, target = routing_policy.decide(result.label, result.confidence)
            output_data["routing_action"] = action.value
            output_data["routing_target"] = target
            logger.info(
                "email_connector.scan_and_classify.routed",
                tenant_id=tenant_id,
                package_id=str(package.package_id),
                workflow_run_id=str(run.id),
                label=result.label,
                confidence=result.confidence,
                action=action.value,
                target=target,
            )

        await repo.update_workflow_run_status(
            run.id,
            "completed",
            output_data=output_data,
        )

        await adapter.acknowledge(package.package_id)

        results.append((str(package.package_id), result))
        logger.info(
            "email_connector.scan_and_classify.item_done",
            tenant_id=tenant_id,
            package_id=str(package.package_id),
            workflow_run_id=str(run.id),
            label=result.label,
            confidence=result.confidence,
            method=result.method,
        )

    return results


def _extract_classifiable_text(package: IntakePackage) -> str:
    """Return EMAIL_BODY text if present, else concatenation of all descriptions."""
    email_bodies = [d.text for d in package.descriptions if d.role == DescriptionRole.EMAIL_BODY]
    if email_bodies:
        return "\n\n".join(t for t in email_bodies if t)
    return "\n\n".join(d.text for d in package.descriptions if d.text)


def _intent_class_is_extract(result: ClassificationResult) -> bool:
    """Sprint Q / S135 — check if the classifier's result falls into the
    EXTRACT abstract class.

    Uses the FU-2 lookup table (``_resolve_intent_class``). The email-
    connector orchestrator calls this gate before running the expensive
    invoice extraction pipeline, so Sprint O's intent_class schema
    groundwork pays off directly here.
    """
    from aiflow.api.v1.emails import _resolve_intent_class

    intent_class = _resolve_intent_class(result.label)
    return intent_class == "EXTRACT"


# Attachment mime types the invoice_processor skill is known to handle.
_INVOICE_EXTRACT_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def _maybe_extract_invoice_fields(
    files: list[IntakeFile],
    *,
    settings: UC3ExtractionSettings,
    workflow_run_id: str | None = None,
) -> dict[str, Any] | None:
    """Sprint Q / S135 — run the invoice_processor extractor on each
    attachment file and return the merged structured-field payload.

    Lazy-imports the skill so the flag-off path never pays the docling or
    gpt-4o cold-start cost. Wrapped in :func:`asyncio.wait_for` against
    ``settings.total_budget_seconds``. Per-file errors are captured per
    ``filename`` — one bad attachment doesn't abort the rest.

    Return shape::

        {
          "extracted_fields": {
             "<filename>": {"vendor": {...}, "buyer": {...}, "header": {...},
                            "line_items": [...], "totals": {...},
                            "extraction_confidence": float,
                            "extraction_time_ms": float,
                            "cost_usd": float, "error": "..."},
             ...
          },
          "total_cost_usd": float,
        }

    Returns ``None`` on timeout or total failure.
    """
    # Lazy import — flag-off must not pay this cost.
    from skills.invoice_processor.workflows.process import (
        extract_invoice_data,
        parse_invoice,
    )

    eligible = [
        f
        for f in files[: settings.max_attachments_per_email]
        if f.mime_type in _INVOICE_EXTRACT_MIMES and Path(f.file_path).exists()
    ]
    if not eligible:
        return {"extracted_fields": {}, "total_cost_usd": 0.0}

    # Approximate cost per file based on gpt-4o-mini pricing — the extractor
    # fires 2 LLM calls/invoice (header + lines), each ~1500 in + ~300 out
    # tokens ≈ 3600 tokens/invoice × $0.15/1M = ~$0.00054. Ceiling per
    # settings stops the loop when projected cost crosses the threshold.
    per_file_budget = settings.extraction_budget_usd

    async def _run() -> dict[str, Any]:
        extracted: dict[str, dict[str, Any]] = {}
        total_cost = 0.0
        for f in eligible:
            filename = f.file_name
            try:
                parse_result = await parse_invoice({"source_path": str(f.file_path)})
                extract_result = await extract_invoice_data(parse_result)
                parsed_files = extract_result.get("files", [])
                if not parsed_files:
                    extracted[filename] = {"error": "no parse output"}
                    continue
                first = parsed_files[0]
                if first.get("error"):
                    extracted[filename] = {"error": first["error"]}
                    continue
                # Approximate per-file cost from token counts if present.
                in_tokens = first.get("_llm_total_input_tokens", 0)
                out_tokens = first.get("_llm_total_output_tokens", 0)
                file_cost = round((in_tokens * 0.15 + out_tokens * 0.6) * 1e-6, 6)
                if file_cost > per_file_budget:
                    extracted[filename] = {
                        "error": f"budget breach: ${file_cost} > ${per_file_budget}"
                    }
                    total_cost += file_cost
                    continue
                extracted[filename] = {
                    "vendor": first.get("vendor", {}),
                    "buyer": first.get("buyer", {}),
                    "header": first.get("header", {}),
                    "line_items": first.get("line_items", []),
                    "totals": first.get("totals", {}),
                    "extraction_confidence": first.get("extraction_confidence", 0.0),
                    "extraction_time_ms": first.get("extraction_time_ms", 0.0),
                    "cost_usd": file_cost,
                }
                total_cost += file_cost
            except Exception as exc:  # pragma: no cover — per-file guard
                logger.info(
                    "email_connector.scan_and_classify.invoice_extract_failed",
                    filename=filename,
                    reason=str(exc),
                )
                extracted[filename] = {"error": f"{type(exc).__name__}: {exc}"}

        return {
            "extracted_fields": extracted,
            "total_cost_usd": round(total_cost, 6),
        }

    try:
        return await asyncio.wait_for(_run(), timeout=settings.total_budget_seconds)
    except TimeoutError:
        logger.info(
            "email_connector.scan_and_classify.invoice_extract_timeout",
            file_count=len(eligible),
            budget_seconds=settings.total_budget_seconds,
            workflow_run_id=workflow_run_id,
        )
        return None
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "email_connector.scan_and_classify.invoice_extract_failed_total",
            reason=str(exc),
            workflow_run_id=workflow_run_id,
        )
        return None


async def _maybe_extract_attachment_features(
    files: list[IntakeFile],
    *,
    settings: UC3AttachmentIntentSettings,
    workflow_run_id: str | None = None,
    team_id: str | None = None,
) -> dict[str, Any] | None:
    """Run AttachmentProcessor over package files + extract features (Sprint O / S127).

    Pure-helper guarded by the caller's flag check — instantiates
    :class:`AttachmentProcessor` lazily so the flag-off path never imports it
    or pays the docling/Azure-DI cold start. Wrapped in
    :func:`asyncio.wait_for` against ``settings.total_budget_seconds`` so a
    docling stall cannot block the classifier path beyond budget.

    FU-7 extension: when ``workflow_run_id`` is provided, emit a
    ``cost_records`` row per processed attachment so per-tenant budgets
    account for docling / Azure DI / LLM-vision spend alongside LLM
    classification cost. Pricing is looked up via
    :class:`aiflow.tools.attachment_cost.AttachmentCostEstimator`.

    Returns ``{"attachment_features": <model_dump>,
    "attachment_text_preview": <first 500 chars of concatenated attachment
    text>}`` (S128 — the preview feeds the optional LLM-context system
    message). Returns ``None`` on timeout / total failure.
    """
    # Lazy import — flag-off must not pay this cost.
    from aiflow.api.cost_recorder import record_cost
    from aiflow.services.classifier.attachment_features import (
        extract_attachment_features,
    )
    from aiflow.tools.attachment_cost import AttachmentCostEstimator
    from aiflow.tools.attachment_processor import AttachmentConfig, AttachmentProcessor

    max_bytes = settings.max_attachment_mb * 1024 * 1024
    processor = AttachmentProcessor(config=AttachmentConfig(max_size_mb=settings.max_attachment_mb))
    cost_estimator = AttachmentCostEstimator()

    async def _run() -> dict[str, Any]:
        processed: list[ProcessedAttachment] = []
        for f in files:
            path = Path(f.file_path)
            if not path.exists():
                continue
            try:
                content = path.read_bytes()
            except OSError as exc:
                logger.info(
                    "email_connector.scan_and_classify.attachment_read_failed",
                    file_id=str(f.file_id),
                    file_name=f.file_name,
                    reason=str(exc),
                )
                continue
            if len(content) > max_bytes:
                continue
            try:
                result = await processor.process(f.file_name, content, f.mime_type)
            except Exception as exc:
                logger.info(
                    "email_connector.scan_and_classify.attachment_process_failed",
                    file_id=str(f.file_id),
                    file_name=f.file_name,
                    reason=str(exc),
                )
                continue
            # AttachmentProcessor's per-layer paths leave ``mime_type`` blank
            # on the ProcessedAttachment. Propagate the upstream IntakeFile
            # mime so the extractor can compute a meaningful ``mime_profile``.
            if not result.mime_type and f.mime_type:
                result.mime_type = f.mime_type
            # FU-7 — annotate metadata with cost + pages so the extractor
            # can sum AttachmentFeatures.total_cost_usd without knowing
            # about pricing.
            cost_usd, pages_processed = cost_estimator.estimate(result)
            result.metadata["cost_usd"] = cost_usd
            result.metadata["pages_processed"] = pages_processed
            processed.append(result)

        features = extract_attachment_features(processed, settings=settings)
        preview_blob = "\n".join(a.text for a in processed if a.text)[:500]

        # FU-7 — emit one cost_records row per processed attachment when the
        # caller threaded a workflow_run_id. Wrap in try/except so a missing
        # DB pool (unit tests, mis-configured env) never blocks the classifier
        # path. ``record_cost`` already swallows its own DB exceptions; this
        # outer guard catches pool bootstrap failures.
        if workflow_run_id:
            for att in processed:
                if att.error:
                    continue
                try:
                    await record_cost(
                        workflow_run_id=workflow_run_id,
                        step_name=f"attachment:{att.processor_used or 'unknown'}",
                        model=att.processor_used or "unknown",
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=float(att.metadata.get("cost_usd") or 0.0),
                        team_id=team_id,
                    )
                except Exception as exc:  # pragma: no cover — defensive
                    logger.info(
                        "email_connector.scan_and_classify.cost_record_skipped",
                        reason=str(exc),
                        filename=att.filename,
                    )

        return {
            "attachment_features": features.model_dump(),
            "attachment_text_preview": preview_blob,
        }

    try:
        return await asyncio.wait_for(_run(), timeout=settings.total_budget_seconds)
    except TimeoutError:
        logger.info(
            "email_connector.scan_and_classify.attachment_extraction_timeout",
            file_count=len(files),
            budget_seconds=settings.total_budget_seconds,
        )
        return None
    except Exception as exc:  # pragma: no cover — defensive guardrail
        logger.warning(
            "email_connector.scan_and_classify.attachment_extraction_failed",
            file_count=len(files),
            reason=str(exc),
        )
        return None


# ---------------------------------------------------------------------------
# Sprint X / SX-2 — UC3 EXTRACT routing through DocRecognizer
# ---------------------------------------------------------------------------


# DocRecognizer doctype names that should keep flowing through the existing
# Sprint Q ``invoice_processor`` byte-stable path. Other known doctypes
# (id_card, address_card, passport, contract) route through DocRecognizer's
# own PromptWorkflow extractor (Sprint W SW-1).
_INVOICE_PROCESSOR_DOCTYPES = {"hu_invoice"}


def build_default_doc_recognizer_orchestrator(
    bootstrap_dir: Path | None = None,
) -> DocumentRecognizerOrchestrator:
    """Lazy-imported factory for the production orchestrator.

    Reads doctype YAMLs from ``data/doctypes`` by default. Tests override
    by passing a constructed orchestrator into ``scan_and_classify`` (or
    by monkeypatching this function).
    """
    from aiflow.services.document_recognizer.orchestrator import (
        DocumentRecognizerOrchestrator,
    )
    from aiflow.services.document_recognizer.registry import DocTypeRegistry

    registry = DocTypeRegistry(bootstrap_dir=bootstrap_dir or Path("data/doctypes"))
    return DocumentRecognizerOrchestrator(registry=registry)


async def _route_extract_by_doctype(
    files: list[IntakeFile],
    *,
    routing_settings: UC3DocRecognizerRoutingSettings,
    extraction_settings: UC3ExtractionSettings,
    tenant_id: str,
    workflow_run_id: str | None = None,
    doc_recognizer_orchestrator: DocumentRecognizerOrchestrator | None = None,
    cost_preflight: CostPreflightGuardrail | None = None,
) -> dict[str, Any] | None:
    """Sprint X / SX-2 — classify each attachment with DocRecognizer and
    dispatch to the right extractor.

    Per-attachment slice of ``routing_settings.total_budget_seconds`` is
    enforced via :func:`asyncio.wait_for`. ``hu_invoice`` doctype dispatches
    back through the byte-stable Sprint Q ``_maybe_extract_invoice_fields``
    helper so UC1 stays bit-stable on the flag-on path. Other known
    doctypes call ``DocumentRecognizerOrchestrator.run`` with the detected
    doctype as a hint and field-map the result into the same per-filename
    dict shape. Below-threshold or unknown doctypes follow
    ``routing_settings.unknown_doctype_action`` (fallback to invoice
    processor / RAG ingest stub / skip).

    Per-attachment errors are isolated (one bad attachment does not
    poison the rest). Per-step cost preflight is consulted when a
    ``cost_preflight`` instance is provided (``allowed=False`` → outcome
    ``refused_cost`` and the LLM call is skipped).

    Return shape::

        {
          "extracted_fields": {<filename>: {...invoice_processor shape OR
                               doc_recognizer extracted_fields...}},
          "total_cost_usd": float,
          "routing_decision": <UC3ExtractRouting.model_dump()>,
        }

    Returns ``None`` only on empty input — every other failure mode is
    surfaced inside the per-attachment record.
    """
    # Lazy imports — flag-off must not pay the DocRecognizer cold start.
    from aiflow.contracts.uc3_routing import UC3AttachmentRoute, UC3ExtractRouting

    if not files:
        return None

    eligible = files[: extraction_settings.max_attachments_per_email]
    if not eligible:
        return None

    orchestrator = doc_recognizer_orchestrator or build_default_doc_recognizer_orchestrator()
    per_attachment_budget = max(
        0.001, routing_settings.total_budget_seconds / max(1, len(eligible))
    )

    extracted_fields: dict[str, Any] = {}
    routes: list[UC3AttachmentRoute] = []
    total_cost = 0.0
    total_latency = 0.0

    for f in eligible:
        attachment_id = str(f.file_id)
        filename = f.file_name
        start = asyncio.get_event_loop().time()
        path: ExtractionPath = "skipped"
        outcome: ExtractionOutcome = "skipped"
        cost_usd = 0.0
        doctype: str | None = None
        confidence = 0.0
        error: str | None = None

        try:
            ctx = await _build_classifier_input(f)
            classify_coro = orchestrator.classify(ctx, tenant_id=tenant_id)
            match, _descriptor = await asyncio.wait_for(
                classify_coro, timeout=per_attachment_budget
            )
            if match is not None:
                doctype = match.doc_type
                confidence = match.confidence

            if match is None or confidence < routing_settings.confidence_threshold:
                # Below-threshold / no-match → policy.
                (
                    path,
                    outcome,
                    cost_usd,
                    fields_for_file,
                    error,
                ) = await _apply_unknown_doctype_action(
                    f,
                    action=routing_settings.unknown_doctype_action,
                    extraction_settings=extraction_settings,
                    cost_preflight=cost_preflight,
                    per_attachment_budget=per_attachment_budget,
                    workflow_run_id=workflow_run_id,
                )
                if fields_for_file is not None:
                    extracted_fields[filename] = fields_for_file
            elif doctype in _INVOICE_PROCESSOR_DOCTYPES:
                preflight_outcome = _check_step_preflight(
                    cost_preflight,
                    step_name="uc3_routing.invoice_processor",
                    ceiling_usd=extraction_settings.extraction_budget_usd,
                )
                if preflight_outcome is not None:
                    path = "invoice_processor"
                    outcome = preflight_outcome
                else:
                    (
                        path,
                        outcome,
                        cost_usd,
                        fields_for_file,
                        error,
                    ) = await _dispatch_to_invoice_processor(
                        f,
                        extraction_settings=extraction_settings,
                        per_attachment_budget=per_attachment_budget,
                        workflow_run_id=workflow_run_id,
                    )
                    if fields_for_file is not None:
                        extracted_fields[filename] = fields_for_file
            else:
                preflight_outcome = _check_step_preflight(
                    cost_preflight,
                    step_name=f"uc3_routing.doc_recognizer.{doctype}",
                    ceiling_usd=extraction_settings.extraction_budget_usd,
                )
                if preflight_outcome is not None:
                    path = "doc_recognizer_workflow"
                    outcome = preflight_outcome
                else:
                    (
                        path,
                        outcome,
                        cost_usd,
                        fields_for_file,
                        error,
                    ) = await _dispatch_to_doc_recognizer(
                        orchestrator,
                        ctx,
                        doctype,
                        tenant_id=tenant_id,
                        per_attachment_budget=per_attachment_budget,
                    )
                    if fields_for_file is not None:
                        extracted_fields[filename] = fields_for_file
        except TimeoutError:
            outcome = "timed_out"
            error = f"per-attachment budget exceeded ({per_attachment_budget:.3f}s)"
            logger.info(
                "email_connector.scan_and_classify.routing_attachment_timeout",
                tenant_id=tenant_id,
                workflow_run_id=workflow_run_id,
                attachment_id=attachment_id,
                filename=filename,
                budget_seconds=per_attachment_budget,
            )
        except Exception as exc:  # noqa: BLE001 — per-attachment isolation
            outcome = "failed"
            error = f"{type(exc).__name__}: {exc}"[:500]
            logger.warning(
                "email_connector.scan_and_classify.routing_attachment_failed",
                tenant_id=tenant_id,
                workflow_run_id=workflow_run_id,
                attachment_id=attachment_id,
                filename=filename,
                reason=error,
            )

        latency_ms = (asyncio.get_event_loop().time() - start) * 1000.0
        total_cost += cost_usd
        total_latency += latency_ms

        routes.append(
            UC3AttachmentRoute(
                attachment_id=attachment_id,
                filename=filename,
                doctype_detected=doctype,
                doctype_confidence=confidence,
                extraction_path=path,
                extraction_outcome=outcome,
                cost_usd=round(cost_usd, 6),
                latency_ms=round(latency_ms, 3),
                error=error,
            )
        )

    routing = UC3ExtractRouting(
        attachments=routes,
        total_cost_usd=round(total_cost, 6),
        total_latency_ms=round(total_latency, 3),
        confidence_threshold=routing_settings.confidence_threshold,
        unknown_doctype_action=routing_settings.unknown_doctype_action,
    )

    return {
        "extracted_fields": extracted_fields,
        "total_cost_usd": routing.total_cost_usd,
        "routing_decision": routing.model_dump(mode="json"),
    }


async def _build_classifier_input(f: IntakeFile) -> ClassifierInput:
    """Build a :class:`ClassifierInput` for a single attachment.

    Reuses :class:`AttachmentProcessor` to extract text — same path the
    Sprint O attachment-features helper uses, so MIME handling stays
    consistent. When the file cannot be read or parsed, returns an empty
    text input (filename + mime_type still feed the rule engine).
    """
    from aiflow.services.document_recognizer.classifier import ClassifierInput
    from aiflow.tools.attachment_processor import AttachmentConfig, AttachmentProcessor

    text = ""
    table_count = 0
    page_count = 1
    path = Path(f.file_path)
    if path.exists():
        try:
            content = path.read_bytes()
            processor = AttachmentProcessor(config=AttachmentConfig(max_size_mb=20))
            processed = await processor.process(f.file_name, content, f.mime_type)
            text = processed.text or ""
            metadata = processed.metadata or {}
            table_count = int(metadata.get("table_count") or 0)
            page_count = int(metadata.get("pages_processed") or metadata.get("page_count") or 1)
        except Exception as exc:  # noqa: BLE001 — degrade to filename-only signals
            logger.info(
                "email_connector.routing.attachment_text_unavailable",
                filename=f.file_name,
                reason=str(exc)[:200],
            )

    return ClassifierInput(
        text=text,
        filename=f.file_name,
        table_count=table_count,
        page_count=page_count,
        mime_type=f.mime_type,
    )


def _check_step_preflight(
    cost_preflight: CostPreflightGuardrail | None,
    *,
    step_name: str,
    ceiling_usd: float | None,
) -> ExtractionOutcome | None:
    """Run :meth:`CostPreflightGuardrail.check_step` if provided.

    Returns ``"refused_cost"`` when the guardrail returned ``allowed=False``,
    otherwise ``None`` (caller proceeds with the extraction). Conservative
    token estimates (1500 in / 300 out) match the Sprint Q pricing notes
    in ``_maybe_extract_invoice_fields``.
    """
    if cost_preflight is None:
        return None
    decision = cost_preflight.check_step(
        step_name=step_name,
        model="gpt-4o-mini",
        input_tokens=1500,
        max_output_tokens=300,
        ceiling_usd=ceiling_usd,
    )
    if not decision.allowed:
        return "refused_cost"
    return None


async def _dispatch_to_invoice_processor(
    f: IntakeFile,
    *,
    extraction_settings: UC3ExtractionSettings,
    per_attachment_budget: float,
    workflow_run_id: str | None,
) -> tuple[ExtractionPath, ExtractionOutcome, float, dict[str, Any] | None, str | None]:
    """Run a single-file invoice extraction via the Sprint Q helper.

    Slices ``per_attachment_budget`` into a one-off
    :class:`UC3ExtractionSettings` so the byte-stable helper enforces the
    routing budget instead of the original 60s default.
    """
    from aiflow.core.config import UC3ExtractionSettings as _UC3ExtractionSettings

    sliced = _UC3ExtractionSettings(
        enabled=True,
        max_attachments_per_email=1,
        total_budget_seconds=per_attachment_budget,
        extraction_budget_usd=extraction_settings.extraction_budget_usd,
    )
    payload = await _maybe_extract_invoice_fields(
        [f], settings=sliced, workflow_run_id=workflow_run_id
    )
    if payload is None:
        return "invoice_processor", "timed_out", 0.0, None, "invoice_processor budget timeout"
    fields = payload["extracted_fields"].get(f.file_name)
    if fields is None or fields.get("error"):
        err = (fields or {}).get("error") or "no extraction output"
        return "invoice_processor", "failed", payload.get("total_cost_usd", 0.0), fields, err
    return (
        "invoice_processor",
        "succeeded",
        float(payload.get("total_cost_usd") or 0.0),
        fields,
        None,
    )


async def _dispatch_to_doc_recognizer(
    orchestrator: DocumentRecognizerOrchestrator,
    ctx: ClassifierInput,
    doctype: str,
    *,
    tenant_id: str,
    per_attachment_budget: float,
) -> tuple[ExtractionPath, ExtractionOutcome, float, dict[str, Any] | None, str | None]:
    """Run :meth:`DocumentRecognizerOrchestrator.run` for non-invoice doctypes."""
    coro = orchestrator.run(ctx, tenant_id=tenant_id, doc_type_hint=doctype)
    triple = await asyncio.wait_for(coro, timeout=per_attachment_budget)
    if triple is None:
        return (
            "doc_recognizer_workflow",
            "failed",
            0.0,
            None,
            "doc_recognizer returned no match",
        )
    _match, extraction, intent = triple
    fields_payload = {
        "doc_type": extraction.doc_type,
        "intent": intent.intent,
        "extracted_fields": {
            name: {"value": fv.value, "confidence": fv.confidence}
            for name, fv in extraction.extracted_fields.items()
        },
        "validation_warnings": list(extraction.validation_warnings),
        "extraction_confidence": min(
            (fv.confidence for fv in extraction.extracted_fields.values()),
            default=0.0,
        ),
        "extraction_time_ms": extraction.extraction_time_ms,
        "cost_usd": extraction.cost_usd,
    }
    return (
        "doc_recognizer_workflow",
        "succeeded",
        float(extraction.cost_usd),
        fields_payload,
        None,
    )


async def _apply_unknown_doctype_action(
    f: IntakeFile,
    *,
    action: str,
    extraction_settings: UC3ExtractionSettings,
    cost_preflight: CostPreflightGuardrail | None,
    per_attachment_budget: float,
    workflow_run_id: str | None,
) -> tuple[ExtractionPath, ExtractionOutcome, float, dict[str, Any] | None, str | None]:
    """Resolve below-threshold / unknown doctype per the configured policy."""
    if action == "fallback_invoice_processor":
        preflight_outcome = _check_step_preflight(
            cost_preflight,
            step_name="uc3_routing.fallback_invoice_processor",
            ceiling_usd=extraction_settings.extraction_budget_usd,
        )
        if preflight_outcome is not None:
            return "invoice_processor", preflight_outcome, 0.0, None, None
        return await _dispatch_to_invoice_processor(
            f,
            extraction_settings=extraction_settings,
            per_attachment_budget=per_attachment_budget,
            workflow_run_id=workflow_run_id,
        )
    if action == "rag_ingest":
        # Sprint X SX-2 placeholder — the actual RAG handoff lands in a
        # later sprint. Record the intent here so the audit trail is
        # complete.
        logger.info(
            "email_connector.scan_and_classify.rag_ingest_stub",
            filename=f.file_name,
            workflow_run_id=workflow_run_id,
        )
        return "rag_ingest", "succeeded", 0.0, {"rag_ingest": "queued"}, None
    # action == "skip"
    return "skipped", "skipped", 0.0, None, None
