"""Pipeline adapter for MetadataEnricherService.enrich."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class EnrichInput(BaseModel):
    """Input schema for metadata enrichment."""

    text: str = Field(..., description="Document text to enrich")
    extract_keywords: bool = Field(True, description="Extract keywords")
    language: str = Field("hu", description="Document language")


class EnrichOutput(BaseModel):
    """Output schema for metadata enrichment."""

    title: str | None = None
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0


class MetadataEnricherAdapter(BaseAdapter):
    """Adapter wrapping MetadataEnricherService.enrich for pipeline use."""

    service_name = "metadata_enricher"
    method_name = "enrich"
    input_schema = EnrichInput
    output_schema = EnrichOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.metadata_enricher.service import (
            MetadataEnricherConfig,
            MetadataEnricherService,
        )

        svc = MetadataEnricherService(config=MetadataEnricherConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, EnrichInput):
            input_data = EnrichInput.model_validate(input_data)
        from aiflow.services.metadata_enricher.service import EnrichmentConfig

        svc = await self._get_service()
        result = await svc.enrich(
            text=config.get("text", input_data.text),
            config=EnrichmentConfig(
                extract_keywords=config.get(
                    "extract_keywords", input_data.extract_keywords
                ),
                language=config.get("language", input_data.language),
            ),
        )
        return {
            "title": result.title,
            "keywords": result.keywords,
            "summary": result.summary,
            "confidence": result.confidence,
        }


adapter_registry.register(MetadataEnricherAdapter())
