"""LiteLLM backend for LLM generation and embedding.

Wraps litellm.acompletion and litellm.aembedding with retry, cost tracking, and structured output.
"""
import time
from typing import Any

import structlog

from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.generation import (
    GenerationInput, GenerationOutput, TextGenerationProtocol,
)
from aiflow.models.protocols.embedding import (
    EmbeddingInput, EmbeddingOutput, EmbeddingProtocol,
)

__all__ = ["LiteLLMBackend"]

logger = structlog.get_logger(__name__)


class LiteLLMBackend(TextGenerationProtocol, EmbeddingProtocol):
    """LiteLLM-based backend supporting 100+ LLM providers."""

    def __init__(self, default_model: str = "openai/gpt-4o-mini", timeout: int = 30) -> None:
        self._default_model = default_model
        self._timeout = timeout

    async def generate(self, input_data: GenerationInput) -> ModelCallResult[GenerationOutput]:
        """Generate text using LiteLLM."""
        import litellm

        model = input_data.model or self._default_model
        start = time.monotonic()

        try:
            if input_data.response_model is not None:
                # Structured output via instructor
                import instructor
                client = instructor.from_litellm(litellm.acompletion)
                result = await client.create(
                    model=model,
                    messages=input_data.messages,
                    response_model=input_data.response_model,
                    temperature=input_data.temperature,
                    max_tokens=input_data.max_tokens,
                    timeout=self._timeout,
                )
                output = GenerationOutput(
                    text=str(result),
                    structured=result,
                    model_used=model,
                )
                # instructor doesn't return usage easily, estimate
                return ModelCallResult(
                    output=output,
                    model_used=model,
                    latency_ms=(time.monotonic() - start) * 1000,
                )
            else:
                response = await litellm.acompletion(
                    model=model,
                    messages=input_data.messages,
                    temperature=input_data.temperature,
                    max_tokens=input_data.max_tokens,
                    stop=input_data.stop,
                    timeout=self._timeout,
                )
                usage = response.usage
                text = response.choices[0].message.content or ""
                output = GenerationOutput(
                    text=text,
                    finish_reason=response.choices[0].finish_reason or "stop",
                    model_used=model,
                )
                cost = litellm.completion_cost(completion_response=response)
                return ModelCallResult(
                    output=output,
                    model_used=model,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    cost_usd=cost,
                    latency_ms=(time.monotonic() - start) * 1000,
                )
        except Exception as e:
            logger.error("litellm_generation_error", model=model, error=str(e))
            raise

    async def embed(self, input_data: EmbeddingInput) -> ModelCallResult[EmbeddingOutput]:
        """Generate embeddings using LiteLLM."""
        import litellm

        model = input_data.model or "openai/text-embedding-3-small"
        start = time.monotonic()

        try:
            response = await litellm.aembedding(model=model, input=input_data.texts)
            embeddings = [item["embedding"] for item in response.data]
            dimensions = len(embeddings[0]) if embeddings else 0
            usage = response.usage
            output = EmbeddingOutput(
                embeddings=embeddings,
                dimensions=dimensions,
                total_tokens=usage.total_tokens if usage else 0,
            )
            return ModelCallResult(
                output=output,
                model_used=model,
                input_tokens=usage.total_tokens if usage else 0,
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            logger.error("litellm_embedding_error", model=model, error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check LiteLLM availability."""
        try:
            import litellm
            return True
        except ImportError:
            return False
