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

from typing import TYPE_CHECKING, Any

import structlog

from aiflow.intake.package import DescriptionRole

if TYPE_CHECKING:
    from aiflow.intake.package import IntakePackage
    from aiflow.policy.intent_routing import IntentRoutingPolicy
    from aiflow.prompts.manager import PromptManager
    from aiflow.services.classifier.service import (
        ClassificationResult,
        ClassifierService,
    )
    from aiflow.sources.base import SourceAdapter
    from aiflow.sources.sink import IntakePackageSink
    from aiflow.state.repository import StateRepository

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

        result = await classifier.classify(text=text, schema_labels=schema_labels)

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
