"""Workflow management endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


class WorkflowInfo(BaseModel):
    """Workflow definition summary."""

    name: str
    description: str = ""
    version: str = "0.1.0"
    step_count: int = 0


class WorkflowListResponse(BaseModel):
    """List of registered workflows."""

    workflows: list[WorkflowInfo]
    total: int


class WorkflowRunRequest(BaseModel):
    """Request to run a workflow."""

    input_data: dict[str, Any] = Field(default_factory=dict)
    async_mode: bool = True
    priority: str = "normal"


class WorkflowRunResponse(BaseModel):
    """Response when a workflow run is accepted."""

    run_id: str
    status: str = "accepted"
    workflow_name: str


# Placeholder registry
_PLACEHOLDER_WORKFLOWS: dict[str, WorkflowInfo] = {
    "document-processing": WorkflowInfo(
        name="document-processing",
        description="Process and ingest documents into vector store",
        step_count=4,
    ),
    "question-answering": WorkflowInfo(
        name="question-answering",
        description="RAG-based question answering pipeline",
        step_count=3,
    ),
}


@router.get("", response_model=WorkflowListResponse)
async def list_workflows() -> WorkflowListResponse:
    """List all registered workflows."""
    workflows = list(_PLACEHOLDER_WORKFLOWS.values())
    return WorkflowListResponse(workflows=workflows, total=len(workflows))


@router.get("/{name}", response_model=WorkflowInfo)
async def get_workflow(name: str) -> WorkflowInfo:
    """Get a specific workflow definition."""
    wf = _PLACEHOLDER_WORKFLOWS.get(name)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    return wf


@router.post("/{name}/run", response_model=WorkflowRunResponse, status_code=202)
async def run_workflow(name: str, request: WorkflowRunRequest) -> WorkflowRunResponse:
    """Run a workflow (placeholder - returns 202 Accepted)."""
    if name not in _PLACEHOLDER_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")

    import uuid

    run_id = str(uuid.uuid4())
    logger.info(
        "workflow_run_accepted",
        workflow=name,
        run_id=run_id,
        async_mode=request.async_mode,
    )
    return WorkflowRunResponse(
        run_id=run_id,
        status="accepted",
        workflow_name=name,
    )
