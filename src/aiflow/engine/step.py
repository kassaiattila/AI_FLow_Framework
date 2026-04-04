"""Step decorator - the atomic building block of AIFlow workflows.

Usage:
    @step(
        name="classify_intent",
        output_types={"category": str, "confidence": float},
        retry=RetryPolicy(max_retries=2),
        timeout=30,
    )
    async def classify_intent(input_data: ClassifyInput, ctx: ExecutionContext,
                               models: ModelClient, prompts: PromptManager) -> ClassifyOutput:
        ...
"""

import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import structlog
from pydantic import BaseModel

from aiflow.engine.policies import RetryPolicy

__all__ = ["step", "StepDefinition"]

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class StepDefinition(BaseModel):
    """Metadata for a registered step."""

    name: str
    output_types: dict[str, type] | None = None
    retry: RetryPolicy | None = None
    timeout: int | None = None
    step_type: str = "standard"  # standard | playwright | shell | human
    description: str = ""

    model_config = {"arbitrary_types_allowed": True}


def step(
    name: str,
    *,
    output_types: dict[str, type] | None = None,
    retry: RetryPolicy | None = None,
    timeout: int | None = None,
    step_type: str = "standard",
    description: str = "",
) -> Callable:
    """Decorator to define a workflow step.

    The decorated function becomes a step that can be used in a WorkflowBuilder.
    It retains its original callable behavior for direct invocation and testing.

    Args:
        name: Unique step name within the workflow
        output_types: Expected output fields and types (Haystack-inspired)
        retry: RetryPolicy for transient error handling
        timeout: Max execution time in seconds
        step_type: standard | playwright | shell | human
        description: Human-readable description
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Store step metadata on the function
        step_def = StepDefinition(
            name=name,
            output_types=output_types,
            retry=retry,
            timeout=timeout,
            step_type=step_type,
            description=description,
        )

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.monotonic()
            _retry = retry or RetryPolicy(max_retries=0)
            _timeout = timeout

            last_error: Exception | None = None

            for attempt in range(_retry.max_retries + 1):
                try:
                    if _timeout:
                        coro = func(*args, **kwargs)
                        import asyncio

                        result = await asyncio.wait_for(coro, timeout=_timeout)
                    else:
                        result = await func(*args, **kwargs)

                    duration = (time.monotonic() - start) * 1000
                    logger.info(
                        "step_completed",
                        step=name,
                        attempt=attempt + 1,
                        duration_ms=round(duration, 1),
                    )
                    return result

                except Exception as e:
                    last_error = e
                    if _retry.should_retry(e, attempt + 1):
                        delay = _retry.get_delay(attempt)
                        logger.warning(
                            "step_retry",
                            step=name,
                            attempt=attempt + 1,
                            error=str(e),
                            error_type=type(e).__name__,
                            delay_seconds=round(delay, 2),
                        )
                        import asyncio

                        await asyncio.sleep(delay)
                    else:
                        duration = (time.monotonic() - start) * 1000
                        logger.error(
                            "step_failed",
                            step=name,
                            attempt=attempt + 1,
                            error=str(e),
                            error_type=type(e).__name__,
                            duration_ms=round(duration, 1),
                        )
                        raise

            # Should not reach here, but safety net
            if last_error:
                raise last_error

        # Attach metadata
        wrapper._step_definition = step_def  # type: ignore[attr-defined]
        wrapper._is_step = True  # type: ignore[attr-defined]

        return wrapper  # type: ignore[return-value]

    return decorator


def get_step_definition(func: Callable) -> StepDefinition | None:
    """Extract StepDefinition from a decorated function."""
    return getattr(func, "_step_definition", None)


def is_step(func: Callable) -> bool:
    """Check if a function is a decorated step."""
    return getattr(func, "_is_step", False)
