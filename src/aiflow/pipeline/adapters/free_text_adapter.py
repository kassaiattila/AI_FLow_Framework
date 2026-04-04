"""Pipeline adapter for FreeTextExtractorService.extract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry


class FreeTextExtractInput(BaseModel):
    """Input schema for free-text extraction."""

    document_id: str = Field(..., description="UUID of the document to query")
    queries: list[dict[str, str]] = Field(
        ..., description="List of {query, hint?} dicts"
    )
    model: str | None = Field(None, description="LLM model override")


class FreeTextExtractOutput(BaseModel):
    """Output schema for free-text extraction."""

    document_id: str = ""
    results: list[dict[str, Any]] = Field(default_factory=list)
    extraction_time_ms: float = 0.0
    model_used: str = ""


class FreeTextExtractAdapter(BaseAdapter):
    """Adapter wrapping FreeTextExtractorService.extract for pipeline use."""

    service_name = "document_extractor"
    method_name = "extract_free_text"
    input_schema = FreeTextExtractInput
    output_schema = FreeTextExtractOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.document_extractor.free_text import (
            FreeTextExtractorService,
        )

        sf = await get_session_factory()
        svc = FreeTextExtractorService(session_factory=sf)
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, FreeTextExtractInput):
            input_data = FreeTextExtractInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        from aiflow.services.document_extractor.free_text import FreeTextQuery

        queries = [
            FreeTextQuery(query=q.get("query", ""), hint=q.get("hint", ""))
            for q in data.queries
        ]

        result = await svc.extract(
            document_id=data.document_id,
            queries=queries,
            model=data.model,
        )

        return {
            "document_id": result.document_id,
            "results": [r.model_dump() for r in result.results],
            "extraction_time_ms": result.extraction_time_ms,
            "model_used": result.model_used,
        }


adapter_registry.register(FreeTextExtractAdapter())
