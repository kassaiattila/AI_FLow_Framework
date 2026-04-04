"""Pipeline adapter for MediaProcessorService.process_media."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry


class ProcessMediaInput(BaseModel):
    """Input schema for media processing."""

    file_path: str = Field(..., description="Path to the media file")
    stt_provider: str | None = Field(None, description="STT provider override")


class ProcessMediaOutput(BaseModel):
    """Output schema for media processing result."""

    job_id: str = ""
    transcript: str = ""
    duration_seconds: float = 0.0
    status: str = ""


class MediaProcessAdapter(BaseAdapter):
    """Adapter wrapping MediaProcessorService.process_media for pipeline use."""

    service_name = "media_processor"
    method_name = "process"
    input_schema = ProcessMediaInput
    output_schema = ProcessMediaOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.registry import ServiceRegistry

        registry = ServiceRegistry()
        return registry.get("media_processor")

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ProcessMediaInput):
            input_data = ProcessMediaInput.model_validate(input_data)
        data = input_data
        svc = self._get_service()

        from pathlib import Path

        result = await svc.process_media(
            file_path=Path(data.file_path),
            stt_provider=data.stt_provider,
            created_by=ctx.user_id,
        )

        return {
            "job_id": getattr(result, "job_id", ""),
            "transcript": getattr(result, "transcript", ""),
            "duration_seconds": getattr(result, "duration_seconds", 0.0),
            "status": getattr(result, "status", ""),
        }


adapter_registry.register(MediaProcessAdapter())
