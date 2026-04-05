"""Pipeline adapter for RerankerService.rerank."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class RerankInput(BaseModel):
    query: str = Field(..., description="Search query")
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    model: str = "bge-reranker-v2-m3"
    return_top: int = 5


class RerankOutput(BaseModel):
    results: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class RerankerAdapter(BaseAdapter):
    service_name = "reranker"
    method_name = "rerank"
    input_schema = RerankInput
    output_schema = RerankOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.reranker.service import RerankerConfig, RerankerService

        svc = RerankerService(config=RerankerConfig())
        await svc.start()
        return svc

    async def _run(
        self, input_data: BaseModel, config: dict[str, Any], ctx: ExecutionContext
    ) -> dict[str, Any]:
        if not isinstance(input_data, RerankInput):
            input_data = RerankInput.model_validate(input_data)
        from aiflow.services.reranker.service import RerankConfig

        svc = await self._get_service()
        results = await svc.rerank(
            query=config.get("query", input_data.query),
            candidates=config.get("candidates", input_data.candidates),
            config=RerankConfig(
                model=config.get("model", input_data.model),
                return_top=config.get("return_top", input_data.return_top),
            ),
        )
        return {
            "results": [r.model_dump() for r in results],
            "count": len(results),
        }


adapter_registry.register(RerankerAdapter())
