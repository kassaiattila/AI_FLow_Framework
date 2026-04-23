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
        tenant_id: str | None = None,
    ) -> ModelCallResult[GenerationOutput]:
        """Generate text or structured output from LLM.

        ``tenant_id`` is optional. When supplied the Sprint N pre-flight cost
        guardrail may refuse the call with :class:`CostGuardrailRefused` if
        the projected cost exceeds remaining budget. Internal / maintenance
        calls that pass no tenant_id are never gated.
        """
        if tenant_id:
            await _llm_client_preflight(
                tenant_id=tenant_id,
                model=model or "openai/gpt-4o-mini",
                messages=messages,
                max_tokens=max_tokens,
            )
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


async def _llm_client_preflight(
    *,
    tenant_id: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
) -> None:
    """Sprint N / S122 — LLM-client-level pre-flight backstop.

    Estimates prompt tokens from message content (char/4 heuristic) and
    refuses the call via :class:`CostGuardrailRefused` when the guardrail is
    enforced. Flag-off and flag-on-dry-run are both non-blocking; any
    dependency failure is swallowed so a guardrail bug never 500s a call.
    """
    try:
        from aiflow.core.errors import CostGuardrailRefused
        from aiflow.guardrails.cost_preflight import build_guardrail_from_settings

        guardrail = await build_guardrail_from_settings()
        if guardrail is None:
            return

        prompt_chars = sum(len(m.get("content", "")) for m in messages)
        input_tokens = max(prompt_chars // 4, 1)

        decision = await guardrail.check(
            tenant_id=tenant_id,
            model=model,
            input_tokens=input_tokens,
            max_output_tokens=max_tokens,
        )
    except Exception as exc:
        from aiflow.core.errors import CostGuardrailRefused as _Refused

        if isinstance(exc, _Refused):
            raise
        logger.warning(
            "cost_preflight_failed",
            run_context="model_client",
            tenant_id=tenant_id,
            error=str(exc)[:200],
        )
        return

    if decision.allowed:
        return

    raise CostGuardrailRefused(
        tenant_id=tenant_id,
        projected_usd=decision.projected_usd,
        remaining_usd=decision.remaining_usd or 0.0,
        period=decision.period,
        reason=decision.reason,
        dry_run=decision.dry_run,
    )


# Backward compatibility alias
LLMClient = ModelClient
