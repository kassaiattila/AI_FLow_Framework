"""Pipeline adapter for DiagramGeneratorService.generate."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

SUPPORTED_DIAGRAM_TYPES = ("flowchart", "sequence", "bpmn_swimlane")


class GenerateDiagramInput(BaseModel):
    """Input schema for diagram generation."""

    description: str = Field(..., description="Natural language diagram description")
    diagram_type: str = Field(
        "flowchart",
        description="Diagram semantic: flowchart | sequence | bpmn_swimlane",
    )


class GenerateDiagramOutput(BaseModel):
    """Output schema for diagram generation result."""

    diagram_id: str = ""
    mermaid_code: str = ""
    svg_content: str = ""
    diagram_type: str = ""


class DiagramGenerateAdapter(BaseAdapter):
    """Adapter wrapping DiagramGeneratorService.generate for pipeline use."""

    service_name = "diagram_generator"
    method_name = "generate"
    input_schema = GenerateDiagramInput
    output_schema = GenerateDiagramOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.diagram_generator.service import (
            DiagramGeneratorConfig,
            DiagramGeneratorService,
        )

        svc = DiagramGeneratorService(config=DiagramGeneratorConfig())
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, GenerateDiagramInput):
            input_data = GenerateDiagramInput.model_validate(input_data)
        data = input_data

        # Fallback unknown diagram types to flowchart (never silently drop).
        requested_type = data.diagram_type
        if requested_type not in SUPPORTED_DIAGRAM_TYPES:
            requested_type = "flowchart"

        svc = await self._get_service()

        result = await svc.generate(
            user_input=data.description,
            diagram_type=requested_type,
            created_by=ctx.user_id,
        )

        # DiagramRecord exposes the diagram PK as `id` (not `diagram_id`),
        # and svg_content may legitimately be None when Kroki is unavailable.
        return {
            "diagram_id": getattr(result, "id", "") or "",
            "mermaid_code": getattr(result, "mermaid_code", "") or "",
            "svg_content": getattr(result, "svg_content", "") or "",
            "diagram_type": requested_type,
        }


adapter_registry.register(DiagramGenerateAdapter())
