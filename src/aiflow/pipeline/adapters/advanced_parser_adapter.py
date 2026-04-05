"""Pipeline adapter for AdvancedParserService.parse."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class ParseInput(BaseModel):
    """Input schema for document parsing."""

    file_path: str = Field(..., description="Path to the document file")
    parser: str = Field("auto", description="Parser: auto/docling/unstructured/tesseract")
    ocr_enabled: bool = Field(True, description="Enable OCR for scanned documents")


class ParseOutput(BaseModel):
    """Output schema for document parsing."""

    text: str = ""
    pages: int = 0
    parser_used: str = ""
    confidence: float = 0.0


class AdvancedParserAdapter(BaseAdapter):
    """Adapter wrapping AdvancedParserService.parse for pipeline use."""

    service_name = "advanced_parser"
    method_name = "parse"
    input_schema = ParseInput
    output_schema = ParseOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.advanced_parser.service import (
            AdvancedParserConfig,
            AdvancedParserService,
        )

        svc = AdvancedParserService(config=AdvancedParserConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ParseInput):
            input_data = ParseInput.model_validate(input_data)
        from aiflow.services.advanced_parser.service import ParserConfig

        svc = await self._get_service()
        result = await svc.parse(
            file_path=config.get("file_path", input_data.file_path),
            config=ParserConfig(
                parser=config.get("parser", input_data.parser),
                ocr_enabled=config.get("ocr_enabled", input_data.ocr_enabled),
            ),
        )
        return {
            "text": result.text,
            "pages": result.pages,
            "parser_used": result.parser_used,
            "confidence": result.confidence,
        }


adapter_registry.register(AdvancedParserAdapter())
