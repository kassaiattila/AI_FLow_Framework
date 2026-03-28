"""Abstract SpecialistAgent base class.

Specialists are **stateless** workers that receive a typed request, perform
one focused task, and return a typed response.  They must never hold mutable
state between ``execute()`` calls.

Architecture rule: the orchestrator may register at most 6 specialists.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

import structlog

from aiflow.agents.messages import AgentRequest, AgentResponse
from aiflow.core.context import ExecutionContext

__all__ = ["AgentSpec", "SpecialistAgent"]

logger = structlog.get_logger(__name__)

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class AgentSpec(BaseModel):
    """Declarative metadata describing a specialist agent.

    Attributes:
        name: Unique short name used for routing (e.g. ``"summarizer"``).
        description: Human-readable purpose of the specialist.
        input_type: Fully-qualified class name of the expected input model.
        output_type: Fully-qualified class name of the produced output model.
        model: Default LLM model identifier (can be overridden at runtime).
        capabilities: Free-form tags describing what this agent can do
            (e.g. ``["text-generation", "summarization"]``).
    """

    name: str
    description: str = ""
    input_type: str = ""
    output_type: str = ""
    model: str = ""
    capabilities: list[str] = Field(default_factory=list)


class SpecialistAgent(ABC, Generic[TInput, TOutput]):
    """Abstract base for all specialist agents.

    Subclasses **must** implement :pyattr:`spec` and :pymeth:`execute`.

    Statelessness contract:
        ``execute()`` must not read from or write to mutable instance
        attributes.  Any intermediate data lives exclusively on the stack
        or inside the :class:`ExecutionContext`.
    """

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def spec(self) -> AgentSpec:
        """Return the agent specification (name, description, types, etc.)."""
        ...

    @abstractmethod
    async def execute(
        self,
        request: AgentRequest[TInput],
        ctx: ExecutionContext,
    ) -> AgentResponse[TOutput]:
        """Execute the specialist logic.

        This method **must** be stateless: do not store results on ``self``.

        Args:
            request: Typed request envelope with input data and metadata.
            ctx: Request-scoped execution context (tracing, budget, etc.).

        Returns:
            A typed response envelope with output, scores, and status.
        """
        ...

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.spec.name!r}>"
