"""PromptWorkflow read-only API endpoints (Sprint R / S140).

Three endpoints, all flag-gated by
``AIFLOW_PROMPT_WORKFLOWS__ENABLED``:

* ``GET /api/v1/prompts/workflows`` — list known workflows
* ``GET /api/v1/prompts/workflows/{name}`` — full descriptor
* ``GET /api/v1/prompts/workflows/{name}/dry-run`` — descriptor +
  resolved nested ``PromptDefinition`` per step (no LLM call, no
  side effect)

S141 will add the executor; this session ships read-only surface only.
"""

from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aiflow.api.v1.prompts import get_prompt_manager
from aiflow.core.errors import FeatureDisabled
from aiflow.prompts.manager import WorkflowResolutionError
from aiflow.prompts.schema import PromptDefinition
from aiflow.prompts.workflow import PromptWorkflow

__all__ = ["router"]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/prompts/workflows", tags=["prompts", "workflows"])


class WorkflowListItem(BaseModel):
    """One row in the listing response."""

    name: str
    version: str
    step_count: int
    tags: list[str]
    default_label: str


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowListItem]
    total: int
    source: str = "backend"


class WorkflowDryRunResponse(BaseModel):
    workflow: PromptWorkflow
    steps: dict[str, PromptDefinition]
    resolved_label: str
    source: str = "backend"


def _to_listing_item(wf: PromptWorkflow) -> WorkflowListItem:
    return WorkflowListItem(
        name=wf.name,
        version=wf.version,
        step_count=len(wf.steps),
        tags=wf.tags,
        default_label=wf.default_label,
    )


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    source: Literal["local", "langfuse", "both"] = Query(default="local"),
) -> WorkflowListResponse:
    """List workflow descriptors.

    Flag-off → 503 ``FeatureDisabled``.

    Sprint W SW-4 (SR-FU-6) added the ``source`` query param so the admin
    UI can offer a source toggle:

    * ``local`` (default) — local YAML descriptors at ``prompts/workflows/``
    * ``langfuse`` — Langfuse-hosted ``workflow:<name>`` JSON-typed prompts
    * ``both`` — merged, deduplicated by ``name`` (local wins on collision)

    The Langfuse listing surface is shipped as a stub
    (:func:`PromptManager.list_langfuse_workflows`) that returns an empty
    list when the Langfuse client is unavailable or the v4 SDK does not
    expose a cheap list-by-prefix call. Operators flip
    ``source=langfuse`` once a real listing helper lands.
    """
    pm = get_prompt_manager()
    if not pm._workflows_enabled:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "FEATURE_DISABLED", "feature": "prompt_workflows"},
        )

    items: list[WorkflowListItem] = []
    seen: set[str] = set()

    if source in ("local", "both") and pm._workflow_loader is not None:
        for name in pm._workflow_loader.list_local():
            try:
                wf, _ = pm.get_workflow(name)
                items.append(_to_listing_item(wf))
                seen.add(wf.name)
            except WorkflowResolutionError as exc:
                logger.warning(
                    "workflow_router.list_skip_unresolvable",
                    workflow=name,
                    error=str(exc),
                )

    if source in ("langfuse", "both"):
        try:
            for wf in pm.list_langfuse_workflows():
                if wf.name in seen:
                    continue
                items.append(_to_listing_item(wf))
                seen.add(wf.name)
        except Exception as exc:  # noqa: BLE001 — Langfuse is best-effort
            logger.warning("workflow_router.list_langfuse_failed", error=str(exc))

    return WorkflowListResponse(workflows=items, total=len(items))


@router.get("/{name}", response_model=PromptWorkflow)
async def get_workflow(name: str) -> PromptWorkflow:
    """Return the full :class:`PromptWorkflow` descriptor (no nested resolution)."""
    pm = get_prompt_manager()
    if not pm._workflows_enabled:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "FEATURE_DISABLED", "feature": "prompt_workflows"},
        )
    try:
        wf, _ = pm.get_workflow(name)
    except FeatureDisabled as exc:  # belt-and-braces; the early check above handles this
        raise HTTPException(
            status_code=503,
            detail={"error_code": "FEATURE_DISABLED", "feature": exc.feature},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "WORKFLOW_NOT_FOUND", "name": name},
        ) from exc
    except WorkflowResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "WORKFLOW_RESOLUTION_FAILED",
                "workflow": exc.workflow,
                "step_id": exc.step_id,
                "prompt_name": exc.prompt_name,
                "cause": str(exc.__cause__),
            },
        ) from exc
    return wf


@router.get("/{name}/dry-run", response_model=WorkflowDryRunResponse)
async def dry_run_workflow(
    name: str,
    label: str | None = Query(default=None),
) -> WorkflowDryRunResponse:
    """Resolve the workflow + its nested step prompts.

    No LLM call, no side effect. Use the optional ``label`` query param
    to override the workflow's ``default_label``.
    """
    pm = get_prompt_manager()
    if not pm._workflows_enabled:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "FEATURE_DISABLED", "feature": "prompt_workflows"},
        )
    try:
        wf, steps = pm.get_workflow(name, label=label)
    except FeatureDisabled as exc:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "FEATURE_DISABLED", "feature": exc.feature},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "WORKFLOW_NOT_FOUND", "name": name},
        ) from exc
    except WorkflowResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "WORKFLOW_RESOLUTION_FAILED",
                "workflow": exc.workflow,
                "step_id": exc.step_id,
                "prompt_name": exc.prompt_name,
                "cause": str(exc.__cause__),
            },
        ) from exc

    return WorkflowDryRunResponse(
        workflow=wf,
        steps=steps,
        resolved_label=label or wf.default_label,
    )
