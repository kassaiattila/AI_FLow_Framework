"""
@test_registry:
    suite: agents-unit
    component: agents.orchestrator
    covers: [src/aiflow/agents/orchestrator.py]
    phase: 3
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [agents, orchestrator, routing, registration, async]
"""
import pytest
from typing import Any

from aiflow.agents.messages import AgentRequest, AgentResponse, ResponseStatus
from aiflow.agents.specialist import SpecialistAgent, AgentSpec
from aiflow.agents.orchestrator import OrchestratorAgent, MAX_SPECIALISTS
from aiflow.core.context import ExecutionContext


# --- Lightweight test specialists ---


def _make_specialist_class(name: str, description: str = "test") -> type[SpecialistAgent]:
    """Create a concrete SpecialistAgent class with given name."""

    class _Agent(SpecialistAgent):
        _agent_name = name
        _agent_desc = description

        @property
        def spec(self) -> AgentSpec:
            return AgentSpec(
                name=self._agent_name,
                description=self._agent_desc,
                input_type="dict",
                output_type="dict",
            )

        async def execute(self, request: AgentRequest, ctx: ExecutionContext) -> AgentResponse:
            return AgentResponse(
                status=ResponseStatus.SUCCESS,
                output={"agent": self._agent_name},
            )

    # Give each class a unique name to avoid conflicts
    _Agent.__name__ = f"Agent_{name}"
    _Agent.__qualname__ = f"Agent_{name}"
    return _Agent


class _ConcreteOrchestrator(OrchestratorAgent):
    """Minimal concrete orchestrator for testing."""

    async def run(self, task: Any, ctx: ExecutionContext) -> Any:
        return {"status": "done"}


class TestOrchestratorRegistration:
    def test_register_single_specialist(self):
        cls = _make_specialist_class("classifier")
        orch = _ConcreteOrchestrator(specialist_types=[cls])
        assert len(orch.specialist_names) == 1
        assert "classifier" in orch.specialist_names

    def test_register_multiple_specialists(self):
        classes = [
            _make_specialist_class("classifier"),
            _make_specialist_class("extractor"),
            _make_specialist_class("summariser"),
        ]
        orch = _ConcreteOrchestrator(specialist_types=classes)
        assert len(orch.specialist_names) == 3

    def test_max_six_specialists_enforced(self):
        classes_6 = [_make_specialist_class(f"agent_{i}") for i in range(6)]
        orch = _ConcreteOrchestrator(specialist_types=classes_6)
        assert len(orch.specialist_names) == 6

    def test_seven_specialists_raises(self):
        classes_7 = [_make_specialist_class(f"agent_{i}") for i in range(7)]
        with pytest.raises(AssertionError, match="max"):
            _ConcreteOrchestrator(specialist_types=classes_7)

    def test_lookup_specialist_by_name(self):
        classes = [
            _make_specialist_class("extractor"),
            _make_specialist_class("classifier"),
        ]
        orch = _ConcreteOrchestrator(specialist_types=classes)
        found = orch.get_specialist("extractor")
        assert found is not None
        assert found.spec.name == "extractor"

    def test_lookup_missing_specialist_raises(self):
        cls = _make_specialist_class("extractor")
        orch = _ConcreteOrchestrator(specialist_types=[cls])
        with pytest.raises(KeyError):
            orch.get_specialist("nonexistent")


class TestOrchestratorProperties:
    def test_specialist_names_is_list(self):
        orch = _ConcreteOrchestrator(specialist_types=[])
        assert isinstance(orch.specialist_names, list)

    def test_empty_orchestrator(self):
        orch = _ConcreteOrchestrator(specialist_types=[])
        assert len(orch.specialist_names) == 0
