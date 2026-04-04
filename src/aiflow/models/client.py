"""Unified model client facade for all AI model operations.

This is the main entry point for skill developers to interact with models.
Injected via DI as `models: ModelClient` in step functions.
"""

from typing import Any

import structlog

from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.embedding import EmbeddingInput, EmbeddingOutput, EmbeddingProtocol
from aiflow.models.protocols.generation import (
    GenerationInput,
    GenerationOutput,
    TextGenerationProtocol,
)

__all__ = ["ModelClient", "LLMClient"]

logger = structlog.get_logger(__name__)


class ModelClient:
    """Unified facade for all model operations.

    Usage in a step:
        @step(name="classify")
        async def classify(input_data, ctx, models: ModelClient, prompts):
            result = await models.generate(messages=[...], response_model=MyOutput)
    """

    def __init__(
        self,
        generation_backend: TextGenerationProtocol,
        embedding_backend: EmbeddingProtocol | None = None,
    ) -> None:
        self._generation = generation_backend
        self._embedding = embedding_backend

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_model: Any | None = None,
        stop: list[str] | None = None,
    ) -> ModelCallResult[GenerationOutput]:
        """Generate text or structured output from LLM."""
        input_data = GenerationInput(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_model=response_model,
            stop=stop,
        )
        result = await self._generation.generate(input_data)
        logger.info(
            "model_generate",
            model=result.model_used,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            latency_ms=round(result.latency_ms, 1),
        )
        return result

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> ModelCallResult[EmbeddingOutput]:
        """Generate embeddings for texts."""
        if self._embedding is None:
            raise RuntimeError("No embedding backend configured")
        input_data = EmbeddingInput(texts=texts, model=model)
        result = await self._embedding.embed(input_data)
        logger.info(
            "model_embed",
            model=result.model_used,
            text_count=len(texts),
            dimensions=result.output.dimensions,
            latency_ms=round(result.latency_ms, 1),
        )
        return result


# Backward compatibility alias
LLMClient = ModelClient
