"""Pipeline adapter for VectorOpsService.get_collection_health."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class VectorOpsInput(BaseModel):
    """Input schema for vector ops health check."""

    collection_id: str = Field(..., description="Collection identifier")


class VectorOpsOutput(BaseModel):
    """Output schema for vector ops health check."""

    total_vectors: int = 0
    index_type: str = "none"
    fragmentation_pct: float = 0.0


class VectorOpsAdapter(BaseAdapter):
    """Adapter wrapping VectorOpsService.get_collection_health for pipeline use."""

    service_name = "vector_ops"
    method_name = "get_collection_health"
    input_schema = VectorOpsInput
    output_schema = VectorOpsOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.vector_ops.service import VectorOpsConfig, VectorOpsService

        svc = VectorOpsService(session_factory=None, config=VectorOpsConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, VectorOpsInput):
            input_data = VectorOpsInput.model_validate(input_data)

        svc = await self._get_service()
        result = await svc.get_collection_health(
            collection_id=config.get("collection_id", input_data.collection_id),
        )
        return {
            "total_vectors": result.total_vectors,
            "index_type": result.index_type,
            "fragmentation_pct": result.fragmentation_pct,
        }


adapter_registry.register(VectorOpsAdapter())
