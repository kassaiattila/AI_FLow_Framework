"""
@test_registry:
    suite: agents-unit
    component: agents.specialist
    covers: [src/aiflow/agents/specialist.py]
    phase: 3
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [agents, specialist, abstract, spec, async]
"""
import pytest
from pydantic import BaseModel

from aiflow.agents.messages import AgentRequest, AgentResponse, ResponseStatus
from aiflow.agents.specialist import SpecialistAgent, AgentSpec
from aiflow.core.context import ExecutionContext


# --- Concrete test subclass ---


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    echoed: str


class EchoAgent(SpecialistAgent):
    """Minimal concrete specialist for testing."""

    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="echo",
            description="Echoes input text back",
            input_type="EchoInput",
            output_type="EchoOutput",
            capabilities=["echo", "text"],
        )

    async def execute(
        self,
        request: AgentRequest,
        ctx: ExecutionContext,
    ) -> AgentResponse:
        text = (
            request.input_data.text
            if isinstance(request.input_data, EchoInput)
            else request.input_data.get("text", "")
        )
        return AgentResponse(
            status=ResponseStatus.SUCCESS,
            output=EchoOutput(echoed=text),
        )


class TestAgentSpec:
    def test_spec_has_required_fields(self):
        spec = AgentSpec(
            name="classifier",
            description="Classifies documents",
            input_type="ClassifyInput",
            output_type="ClassifyOutput",
        )
        assert spec.name == "classifier"
        assert spec.description == "Classifies documents"
        assert spec.input_type == "ClassifyInput"
        assert spec.output_type == "ClassifyOutput"

    def test_spec_capabilities(self):
        spec = AgentSpec(
            name="summarizer",
            capabilities=["text-generation", "summarization"],
        )
        assert "text-generation" in spec.capabilities
        assert "summarization" in spec.capabilities

    def test_spec_default_values(self):
        spec = AgentSpec(name="minimal")
        assert spec.description == ""
        assert spec.input_type == ""
        assert spec.output_type == ""
        assert spec.model == ""
        assert spec.capabilities == []

    def test_spec_equality(self):
        kwargs = dict(
            name="a",
            description="d",
            input_type="In",
            output_type="Out",
        )
        s1 = AgentSpec(**kwargs)
        s2 = AgentSpec(**kwargs)
        assert s1 == s2


class TestSpecialistAgent:
    def test_concrete_subclass_instantiates(self):
        agent = EchoAgent()
        assert agent is not None

    def test_spec_property_returns_correct_metadata(self):
        agent = EchoAgent()
        spec = agent.spec
        assert spec.name == "echo"
        assert spec.description == "Echoes input text back"
        assert "echo" in spec.capabilities

    @pytest.mark.asyncio
    async def test_execute_returns_agent_response(self):
        agent = EchoAgent()
        ctx = ExecutionContext(run_id="test-spec-001")
        req = AgentRequest(input_data=EchoInput(text="hello"))
        resp = await agent.execute(req, ctx)
        assert isinstance(resp, AgentResponse)
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.output.echoed == "hello"

    @pytest.mark.asyncio
    async def test_specialist_is_stateless(self):
        """Calling execute twice must not alter the agent's internal state."""
        agent = EchoAgent()
        initial_attrs = dict(vars(agent))  # snapshot
        ctx = ExecutionContext(run_id="stateless-test")
        req1 = AgentRequest(input_data=EchoInput(text="first"))
        req2 = AgentRequest(input_data=EchoInput(text="second"))
        await agent.execute(req1, ctx)
        await agent.execute(req2, ctx)
        assert dict(vars(agent)) == initial_attrs

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self):
        agent = EchoAgent()
        ctx = ExecutionContext(run_id="meta-test")
        req = AgentRequest(
            input_data=EchoInput(text="world"),
            context_metadata={"trace_id": "tr-42"},
            max_retries=1,
        )
        resp = await agent.execute(req, ctx)
        assert resp.output.echoed == "world"

    def test_cannot_instantiate_abstract_directly(self):
        with pytest.raises(TypeError):
            SpecialistAgent()

    def test_repr(self):
        agent = EchoAgent()
        r = repr(agent)
        assert "EchoAgent" in r
        assert "echo" in r
