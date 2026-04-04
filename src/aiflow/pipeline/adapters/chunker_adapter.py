"""Pipeline adapter for AdvancedChunkerService.chunk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class ChunkInput(BaseModel):
    """Input schema for text chunking."""

    text: str = Field(..., description="Text to chunk")
    strategy: str = Field("recursive", description="Chunking strategy")
    chunk_size: int = Field(512, description="Target chunk size in characters")
    chunk_overlap: int = Field(64, description="Overlap between chunks")


class ChunkOutput(BaseModel):
    """Output schema for text chunking."""

    chunks: list[dict[str, Any]] = Field(default_factory=list)
    total_chunks: int = 0
    strategy_used: str = ""


class ChunkerAdapter(BaseAdapter):
    """Adapter wrapping AdvancedChunkerService.chunk for pipeline use."""

    service_name = "advanced_chunker"
    method_name = "chunk"
    input_schema = ChunkInput
    output_schema = ChunkOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.advanced_chunker.service import (
            AdvancedChunkerConfig,
            AdvancedChunkerService,
        )

        svc = AdvancedChunkerService(config=AdvancedChunkerConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ChunkInput):
            input_data = ChunkInput.model_validate(input_data)
        from aiflow.services.advanced_chunker.service import ChunkConfig

        svc = await self._get_service()
        result = await svc.chunk(
            text=config.get("text", input_data.text),
            config=ChunkConfig(
                strategy=config.get("strategy", input_data.strategy),
                chunk_size=config.get("chunk_size", input_data.chunk_size),
                chunk_overlap=config.get("chunk_overlap", input_data.chunk_overlap),
            ),
        )
        return {
            "chunks": result.chunks,
            "total_chunks": result.total_chunks,
            "strategy_used": result.strategy_used,
        }


adapter_registry.register(ChunkerAdapter())
