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
    from aiflow.core.config import UC3AttachmentIntentSettings
    from aiflow.intake.package import IntakeFile, IntakePackage
    from aiflow.policy.intent_routing import IntentRoutingPolicy
    from aiflow.prompts.manager import PromptManager
    from aiflow.services.classifier.service import (
        ClassificationResult,
        ClassifierService,
    )
    from aiflow.sources.base import SourceAdapter
    from aiflow.sources.sink import IntakePackageSink
    from aiflow.state.repository import StateRepository
    from aiflow.tools.attachment_processor import ProcessedAttachment

# Runtime references — keep these visible to ruff so the autoformatter
# doesn't strip them as unused on subsequent edits.
_RUNTIME_HOOKS = (asyncio, Path)

__all__ = ["scan_and_classify"]

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

        result = await classifier.classify(
            text=text,
            schema_labels=schema_labels,
            context=classifier_context,
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
