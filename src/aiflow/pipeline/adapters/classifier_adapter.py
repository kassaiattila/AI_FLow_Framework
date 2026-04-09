"""Pipeline adapter for ClassifierService.classify."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry


class ClassifyInput(BaseModel):
    """Input schema for classification."""

    text: str = Field(..., description="Text to classify")
    subject: str = Field("", description="Optional subject line")
    strategy: str | None = Field(None, description="Classification strategy override")
    schema_labels: list[dict[str, Any]] | None = Field(None, description="Custom label definitions")


class ClassifyOutput(BaseModel):
    """Output schema for classification result."""

    label: str = ""
    confidence: float = 0.0
    method: str = ""
    all_scores: dict[str, float] = Field(default_factory=dict)


class ClassifierAdapter(BaseAdapter):
    """Adapter wrapping ClassifierService.classify for pipeline use."""

    service_name = "classifier"
    method_name = "classify"
    input_schema = ClassifyInput
    output_schema = ClassifyOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.classifier.service import ClassifierConfig, ClassifierService

        svc = ClassifierService(config=ClassifierConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ClassifyInput):
            input_data = ClassifyInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        result = await svc.classify(
            text=data.text,
            subject=data.subject,
            schema_labels=data.schema_labels,
            strategy=data.strategy,
        )

        return {
            "label": getattr(result, "label", ""),
            "confidence": getattr(result, "confidence", 0.0),
            "method": getattr(result, "method", ""),
            "all_scores": getattr(result, "all_scores", {}),
        }


adapter_registry.register(ClassifierAdapter())
