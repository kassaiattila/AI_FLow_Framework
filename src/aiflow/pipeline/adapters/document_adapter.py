"""Pipeline adapter for DocumentExtractorService.extract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry


class ExtractDocumentInput(BaseModel):
    """Input schema for document extraction."""

    file_path: str = Field(..., description="Path to the document file")
    config_name: str | None = Field(None, description="Document type config name override")


class ExtractDocumentOutput(BaseModel):
    """Output schema for document extraction result."""

    document_id: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    validation_errors: list[str] = Field(default_factory=list)
    raw_text: str = ""


class DocumentExtractAdapter(BaseAdapter):
    """Adapter wrapping DocumentExtractorService.extract for pipeline use."""

    service_name = "document_extractor"
    method_name = "extract"
    input_schema = ExtractDocumentInput
    output_schema = ExtractDocumentOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.document_extractor.service import (
            DocumentExtractorConfig,
            DocumentExtractorService,
        )

        sf = await get_session_factory()
        svc = DocumentExtractorService(session_factory=sf, config=DocumentExtractorConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ExtractDocumentInput):
            input_data = ExtractDocumentInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        result = await svc.extract(
            file_path=data.file_path,
            config_name=data.config_name,
        )

        return {
            "document_id": getattr(result, "invoice_id", getattr(result, "document_id", "")),
            "fields": getattr(result, "fields", {}),
            "confidence": getattr(result, "confidence", 0.0),
            "validation_errors": getattr(result, "validation_errors", []),
            "raw_text": getattr(result, "raw_text", ""),
        }


adapter_registry.register(DocumentExtractAdapter())
