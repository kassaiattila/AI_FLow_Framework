"""OrchestratorAgent -- the single top-level coordinator.

Architecture rule: **max 2 levels** (one orchestrator + at most 6 specialists).
The orchestrator instantiates its specialists at construction time, validates
the hard cap, and exposes helpers to delegate work and evaluate quality gates.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

import structlog

from aiflow.agents.messages import AgentRequest, AgentResponse, ResponseStatus
from aiflow.agents.quality_gate import QualityGate, QualityGateResult
from aiflow.agents.specialist import SpecialistAgent
from aiflow.core.context import ExecutionContext
from aiflow.core.errors import QualityGateFailedError

__all__ = ["OrchestratorAgent"]

logger = structlog.get_logger(__name__)

MAX_SPECIALISTS = 6

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class OrchestratorAgent(ABC):
    """Base class for the single orchestrator in a 2-level agent system.

    Args:
        specialist_types: Concrete :class:`SpecialistAgent` **types** (classes,
            not instances).  The orchestrator instantiates each one.  At most
            6 are allowed.
        quality_gates: Optional list of :class:`QualityGate` definitions
            applied after specialist executions.

    Raises:
        AssertionError: If more than 6 specialist types are supplied.
    """

    def __init__(
        self,
        specialist_types: list[type[SpecialistAgent]],  # type: ignore[type-arg]
        quality_gates: list[QualityGate] | None = None,
    ) -> None:
        assert len(specialist_types) <= MAX_SPECIALISTS, (
            f"Architecture violation: max {MAX_SPECIALISTS} specialists allowed, "
            f"got {len(specialist_types)}"
        )

        # Instantiate each specialist (they are stateless, so one instance suffices).
        self._specialists: dict[str, SpecialistAgent] = {}  # type: ignore[type-arg]
        for cls in specialist_types:
            instance = cls()
            name = instance.spec.name
            self._specialists[name] = instance
            logger.info(
                "specialist_registered",
                specialist=name,
                capabilities=instance.spec.capabilities,
            )

        self._quality_gates: list[QualityGate] = quality_gates or []
        logger.info(
            "orchestrator_init",
            specialist_count=len(self._specialists),
            gate_count=len(self._quality_gates),
        )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def run(
        self,
        task: Any,
        ctx: ExecutionContext,
    ) -> Any:
        """Route and execute a high-level task via specialists.

        Subclasses implement the concrete routing / sequencing logic.

        Args:
            task: Application-defined task description or request object.
            ctx: Request-scoped execution context.

        Returns:
            Application-defined result.
        """
        ...

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    async def delegate(
        self,
        specialist_name: str,
        request: AgentRequest[TInput],
        ctx: ExecutionContext,
    ) -> AgentResponse[TOutput]:
        """Delegate work to a registered specialist by name.

        After the specialist responds the orchestrator automatically evaluates
        any configured quality gates against the returned scores.

        Args:
            specialist_name: The ``spec.name`` of the target specialist.
            request: Typed request envelope.
            ctx: Request-scoped execution context.

        Returns:
            The specialist's response, potentially augmented with gate results.

        Raises:
            KeyError: If *specialist_name* is not registered.
            QualityGateFailedError: If a gate fails with ``reject`` action.
        """
        specialist = self._specialists[specialist_name]
        log = logger.bind(specialist=specialist_name)
        log.info("delegating")

        response: AgentResponse = await specialist.execute(request, ctx)  # type: ignore[type-arg]

        # Evaluate quality gates against the response scores.
        gate_results = self._evaluate_gates(response.scores)
        for gr in gate_results:
            if not gr.passed:
                log.warning(
                    "quality_gate_failed",
                    gate=gr.gate_name,
                    metric_value=gr.metric_value,
                    action=gr.action_taken,
                )
                if gr.action_taken == "reject":
                    raise QualityGateFailedError(
                        f"Quality gate '{gr.gate_name}' rejected output "
                        f"(score={gr.metric_value:.3f})",
                        details={"gate": gr.gate_name, "metric_value": gr.metric_value},
                    )
                if gr.action_taken == "escalate":
                    response.status = ResponseStatus.NEEDS_REVIEW

        log.info(
            "delegation_complete",
            status=response.status,
            duration_ms=response.duration_ms,
        )
        return response  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Quality gate helpers
    # ------------------------------------------------------------------

    def _evaluate_gates(self, scores: dict[str, float]) -> list[QualityGateResult]:
        """Run all configured quality gates against *scores*."""
        return [gate.evaluate(scores) for gate in self._quality_gates]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def specialist_names(self) -> list[str]:
        """Return the names of all registered specialists."""
        return list(self._specialists.keys())

    def get_specialist(self, name: str) -> SpecialistAgent:  # type: ignore[type-arg]
        """Return the specialist instance registered under *name*."""
        return self._specialists[name]
