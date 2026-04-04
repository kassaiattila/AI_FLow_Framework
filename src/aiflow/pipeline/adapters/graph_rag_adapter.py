"""Pipeline adapter for GraphRAGService.extract_entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class GraphEntityInput(BaseModel):
    """Input schema for entity extraction."""

    text: str = Field(..., description="Text to extract entities from")


class GraphEntityOutput(BaseModel):
    """Output schema for entity extraction."""

    entities: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class GraphRAGAdapter(BaseAdapter):
    """Adapter wrapping GraphRAGService.extract_entities for pipeline use."""

    service_name = "graph_rag"
    method_name = "extract_entities"
    input_schema = GraphEntityInput
    output_schema = GraphEntityOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.graph_rag.service import GraphRAGConfig, GraphRAGService

        svc = GraphRAGService(config=GraphRAGConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, GraphEntityInput):
            input_data = GraphEntityInput.model_validate(input_data)

        svc = await self._get_service()
        entities = await svc.extract_entities(
            text=config.get("text", input_data.text),
        )
        return {
            "entities": entities,
            "count": len(entities),
        }


adapter_registry.register(GraphRAGAdapter())
