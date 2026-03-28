"""
@test_registry:
    suite: agents-unit
    component: agents.messages
    covers: [src/aiflow/agents/messages.py]
    phase: 3
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [agents, messages, request, response, generics]
"""
import pytest
from pydantic import BaseModel, ValidationError

from aiflow.agents.messages import AgentRequest, AgentResponse, ResponseStatus


class SamplePayload(BaseModel):
    text: str
    count: int = 1


class SampleResult(BaseModel):
    answer: str
    confidence: float = 0.0


class TestResponseStatus:
    def test_status_values(self):
        assert ResponseStatus.SUCCESS == "success"
        assert ResponseStatus.FAILED == "failed"
        assert ResponseStatus.NEEDS_REVIEW == "needs_review"

    def test_status_is_str(self):
        assert isinstance(ResponseStatus.SUCCESS, str)


class TestAgentRequest:
    def test_creation_with_input_data(self):
        req = AgentRequest(input_data={"text": "hello"})
        assert req.input_data == {"text": "hello"}

    def test_creation_with_typed_input(self):
        payload = SamplePayload(text="hello", count=3)
        req = AgentRequest[SamplePayload](input_data=payload)
        assert req.input_data.text == "hello"
        assert req.input_data.count == 3

    def test_metadata_and_max_retries(self):
        req = AgentRequest(
            input_data="anything",
            context_metadata={"trace_id": "abc-123", "user": "tester"},
            max_retries=5,
        )
        assert req.context_metadata["trace_id"] == "abc-123"
        assert req.max_retries == 5

    def test_default_metadata_empty(self):
        req = AgentRequest(input_data="x")
        assert req.context_metadata == {}

    def test_default_max_retries(self):
        req = AgentRequest(input_data="x")
        assert req.max_retries == 3

    def test_max_retries_validation_lower_bound(self):
        with pytest.raises(ValidationError):
            AgentRequest(input_data="x", max_retries=-1)

    def test_max_retries_validation_upper_bound(self):
        with pytest.raises(ValidationError):
            AgentRequest(input_data="x", max_retries=11)


class TestAgentResponse:
    def test_success_status(self):
        resp = AgentResponse(status=ResponseStatus.SUCCESS, output="done")
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.output == "done"

    def test_failed_with_error(self):
        resp = AgentResponse(
            status=ResponseStatus.FAILED,
            error="LLM timed out",
        )
        assert resp.status == ResponseStatus.FAILED
        assert resp.error == "LLM timed out"
        assert resp.output is None

    def test_with_scores(self):
        resp = AgentResponse(
            status=ResponseStatus.SUCCESS,
            output={"answer": "42"},
            scores={"accuracy": 0.95, "relevance": 0.88},
        )
        assert resp.scores["accuracy"] == 0.95
        assert resp.scores["relevance"] == 0.88

    def test_needs_review_status(self):
        resp = AgentResponse(status=ResponseStatus.NEEDS_REVIEW)
        assert resp.status == ResponseStatus.NEEDS_REVIEW

    def test_default_status_is_success(self):
        resp = AgentResponse()
        assert resp.status == ResponseStatus.SUCCESS

    def test_default_scores_empty(self):
        resp = AgentResponse()
        assert resp.scores == {}

    def test_default_output_none(self):
        resp = AgentResponse()
        assert resp.output is None

    def test_default_error_none(self):
        resp = AgentResponse()
        assert resp.error is None

    def test_duration_ms(self):
        resp = AgentResponse(duration_ms=123.4)
        assert resp.duration_ms == 123.4

    def test_typed_output(self):
        result = SampleResult(answer="42", confidence=0.99)
        resp = AgentResponse[SampleResult](
            status=ResponseStatus.SUCCESS,
            output=result,
        )
        assert resp.output.answer == "42"
        assert resp.output.confidence == 0.99
