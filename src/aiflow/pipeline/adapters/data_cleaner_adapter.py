"""Pipeline adapter for DataCleanerService.clean."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class CleanInput(BaseModel):
    """Input schema for document cleaning."""

    text: str = Field(..., description="Raw document text to clean")
    normalize_whitespace: bool = Field(True, description="Normalize whitespace")
    language: str = Field("hu", description="Document language")


class CleanOutput(BaseModel):
    """Output schema for document cleaning."""

    cleaned_text: str = ""
    original_length: int = 0
    cleaned_length: int = 0


class DataCleanerAdapter(BaseAdapter):
    """Adapter wrapping DataCleanerService.clean for pipeline use."""

    service_name = "data_cleaner"
    method_name = "clean"
    input_schema = CleanInput
    output_schema = CleanOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.data_cleaner.service import (
            DataCleanerConfig,
            DataCleanerService,
        )

        svc = DataCleanerService(config=DataCleanerConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, CleanInput):
            input_data = CleanInput.model_validate(input_data)
        from aiflow.services.data_cleaner.service import CleaningConfig

        svc = await self._get_service()
        result = await svc.clean(
            text=config.get("text", input_data.text),
            config=CleaningConfig(
                normalize_whitespace=config.get(
                    "normalize_whitespace", input_data.normalize_whitespace
                ),
                language=config.get("language", input_data.language),
            ),
        )
        return {
            "cleaned_text": result.cleaned_text,
            "original_length": result.original_length,
            "cleaned_length": result.cleaned_length,
        }


adapter_registry.register(DataCleanerAdapter())
