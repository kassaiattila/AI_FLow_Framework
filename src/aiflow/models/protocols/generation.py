"""Text generation protocol (LLM chat/completion)."""

from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from aiflow.models.protocols.base import BaseModelProtocol, ModelCallResult

__all__ = ["GenerationInput", "GenerationOutput", "TextGenerationProtocol"]


class GenerationInput(BaseModel):
    """Input for text generation."""

    messages: list[dict[str, str]]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    response_model: Any | None = None  # Pydantic model for structured output
    stop: list[str] | None = None


class GenerationOutput(BaseModel):
    """Output from text generation."""

    text: str
    structured: Any | None = None  # Parsed Pydantic model if response_model was given
    finish_reason: str = "stop"
    model_used: str = ""


class TextGenerationProtocol(BaseModelProtocol):
    """Protocol for LLM text generation."""

    @abstractmethod
    async def generate(
        self,
        input_data: GenerationInput,
    ) -> ModelCallResult[GenerationOutput]:
        """Generate text from messages."""
        ...
