"""Pipeline adapter for the Spec Writer skill workflow (B5.2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry


class WriteSpecInput(BaseModel):
    """Input schema for the spec_writer pipeline adapter."""

    raw_text: str = Field(..., description="Free-form description of what to spec out")
    spec_type: Literal["feature", "api", "db", "user_story"] = "feature"
    language: Literal["hu", "en"] = "hu"
    context: str | None = None


class WriteSpecOutput(BaseModel):
    """Output schema for the spec_writer pipeline adapter."""

    title: str = ""
    spec_type: str = ""
    language: str = ""
    final_markdown: str = ""
    score: float = 0.0
    is_acceptable: bool = False
    sections_count: int = 0
    word_count: int = 0


class SpecWriterAdapter(BaseAdapter):
    """Adapter wrapping the Spec Writer skill workflow for pipeline use."""

    service_name = "spec_writer"
    method_name = "write"
    input_schema = WriteSpecInput
    output_schema = WriteSpecOutput

    def __init__(self, runner: Any = None) -> None:
        self._runner = runner

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, WriteSpecInput):
            input_data = WriteSpecInput.model_validate(input_data)
        data = input_data

        # Lazy import — keeps adapter discovery cheap and avoids an upfront
        # LiteLLM backend allocation when the adapter is never invoked.
        from skills.spec_writer.models import SpecInput
        from skills.spec_writer.workflows.spec_writing import run_spec_writing

        inp = SpecInput(
            raw_text=data.raw_text,
            spec_type=data.spec_type,
            language=data.language,
            context=data.context,
        )

        if self._runner is not None:
            result = await self._runner(inp)
        else:
            result = await run_spec_writing(inp)

        return {
            "title": result.draft.title,
            "spec_type": result.draft.spec_type,
            "language": result.draft.language,
            "final_markdown": result.final_markdown,
            "score": result.review.score,
            "is_acceptable": result.review.is_acceptable,
            "sections_count": result.draft.sections_count,
            "word_count": result.draft.word_count,
        }


adapter_registry.register(SpecWriterAdapter())
