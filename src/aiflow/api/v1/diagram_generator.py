"""Diagram Generator API endpoints — F4a.

CRUD + generate + export for persisted BPMN diagrams.
"""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/diagrams", tags=["diagrams"])

_service = None


def _get_service():
    global _service
    if _service is None:
        from aiflow.services.diagram_generator import DiagramGeneratorService
        _service = DiagramGeneratorService()
    return _service


class GenerateRequest(BaseModel):
    user_input: str
    created_by: str | None = None


class DiagramResponse(BaseModel):
    id: str
    user_input: str
    mermaid_code: str
    drawio_xml: str | None = None
    bpmn_xml: str | None = None
    svg_content: str | None = None
    review: dict[str, Any] | None = None
    export_formats: list[str] = []
    created_by: str | None = None
    created_at: str = ""
    updated_at: str = ""
    source: str = "backend"


class DiagramListResponse(BaseModel):
    diagrams: list[DiagramResponse]
    total: int
    source: str = "backend"


@router.post("/generate", response_model=DiagramResponse)
async def generate_diagram(request: GenerateRequest) -> DiagramResponse:
    """Generate a BPMN diagram from natural language and persist it."""
    if not request.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input is required")
    try:
        svc = _get_service()
        record = await svc.generate(request.user_input, created_by=request.created_by)
        return DiagramResponse(**record.model_dump(), source="backend")
    except Exception as e:
        logger.error("diagram_generate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DiagramListResponse)
async def list_diagrams(limit: int = 50, offset: int = 0) -> DiagramListResponse:
    """List all persisted diagrams."""
    svc = _get_service()
    diagrams, total = await svc.list_diagrams(limit=limit, offset=offset)
    return DiagramListResponse(
        diagrams=[DiagramResponse(**d.model_dump(), source="backend") for d in diagrams],
        total=total,
    )


@router.get("/{diagram_id}", response_model=DiagramResponse)
async def get_diagram(diagram_id: str) -> DiagramResponse:
    """Get a single diagram by ID."""
    svc = _get_service()
    record = await svc.get_diagram(diagram_id)
    if not record:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return DiagramResponse(**record.model_dump(), source="backend")


@router.delete("/{diagram_id}")
async def delete_diagram(diagram_id: str):
    """Delete a diagram by ID."""
    svc = _get_service()
    deleted = await svc.delete_diagram(diagram_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return {"deleted": True, "source": "backend"}


@router.get("/{diagram_id}/export/{fmt}")
async def export_diagram(diagram_id: str, fmt: str) -> PlainTextResponse:
    """Export a diagram in the requested format (mermaid, svg, drawio, bpmn)."""
    if fmt not in ("mermaid", "svg", "drawio", "bpmn"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")
    svc = _get_service()
    content = await svc.export_diagram(diagram_id, fmt=fmt)
    if content is None:
        detail = f"Export not available for format: {fmt}."
        if fmt == "svg":
            detail += " SVG requires Kroki service (docker compose up -d kroki) or a previous render."
        raise HTTPException(status_code=404, detail=detail)
    content_types = {"mermaid": "text/plain", "svg": "image/svg+xml", "drawio": "application/xml", "bpmn": "application/xml"}
    return PlainTextResponse(content=content, media_type=content_types.get(fmt, "text/plain"))
