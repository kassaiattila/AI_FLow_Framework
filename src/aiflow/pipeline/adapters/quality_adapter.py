"""Pipeline adapter for QualityService.evaluate_rubric."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class QualityEvalInput(BaseModel):
    """Input schema for rubric evaluation."""

    actual: str = Field(..., description="Actual LLM output to evaluate")
    rubric: str = Field(..., description="Rubric name or custom rubric text")
    expected: str | None = Field(None, description="Expected output for comparison")


class QualityEvalOutput(BaseModel):
    """Output schema for rubric evaluation."""

    score: float = 0.0
    pass_: bool = False
    reasoning: str = ""


class QualityEvalAdapter(BaseAdapter):
    """Adapter wrapping QualityService.evaluate_rubric for pipeline use."""

    service_name = "quality"
    method_name = "evaluate_rubric"
    input_schema = QualityEvalInput
    output_schema = QualityEvalOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.quality.service import (
            QualityConfig,
            QualityService,
        )

        svc = QualityService(config=QualityConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, QualityEvalInput):
            input_data = QualityEvalInput.model_validate(input_data)

        svc = await self._get_service()

        result = await svc.evaluate_rubric(
            actual=config.get("actual", input_data.actual),
            rubric=config.get("rubric", input_data.rubric),
            expected=config.get("expected", input_data.expected),
        )

        return {
            "score": result.score,
            "pass_": result.pass_,
            "reasoning": result.reasoning,
        }


adapter_registry.register(QualityEvalAdapter())
