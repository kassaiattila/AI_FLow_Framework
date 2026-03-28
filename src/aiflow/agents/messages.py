"""Generic typed request/response for agent communication.

AgentRequest[TInput] and AgentResponse[TOutput] provide a uniform envelope
for all specialist interactions, keeping payload types explicit via generics.
"""

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

__all__ = ["AgentRequest", "AgentResponse", "ResponseStatus"]

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class ResponseStatus(StrEnum):
    """Possible outcomes of an agent execution."""

    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class AgentRequest(BaseModel, Generic[TInput]):
    """Typed request envelope sent to a specialist agent.

    Attributes:
        input_data: The strongly-typed payload for the specialist.
        context_metadata: Arbitrary key/value pairs forwarded from the
            orchestrator (e.g. trace ids, user info).
        max_retries: How many times the orchestrator may re-send on failure.
    """

    input_data: TInput
    context_metadata: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)

    model_config = {"arbitrary_types_allowed": True}


class AgentResponse(BaseModel, Generic[TOutput]):
    """Typed response envelope returned by a specialist agent.

    Attributes:
        status: Outcome of the execution.
        output: The strongly-typed result (None on failure).
        scores: Named quality scores produced during execution
            (e.g. ``{"accuracy": 0.92, "relevance": 0.87}``).
        error: Human-readable error description when status is *failed*.
        duration_ms: Wall-clock execution time in milliseconds.
    """

    status: ResponseStatus = ResponseStatus.SUCCESS
    output: TOutput | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float | None = None

    model_config = {"arbitrary_types_allowed": True}
