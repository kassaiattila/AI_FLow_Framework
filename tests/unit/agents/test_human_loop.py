"""
@test_registry:
    suite: agents-unit
    component: agents.human_loop
    covers: [src/aiflow/agents/human_loop.py]
    phase: 3
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [agents, human_loop, review, escalation, async]
"""
import pytest
from datetime import UTC, datetime, timedelta

from aiflow.agents.human_loop import HumanReviewRequest, HumanReviewResponse, HumanLoopManager
from aiflow.core.errors import HumanReviewRequiredError


class TestHumanReviewRequest:
    def test_creation_with_all_fields(self):
        deadline = datetime.now(UTC) + timedelta(minutes=30)
        req = HumanReviewRequest(
            workflow_run_id="run-42",
            step_name="extract",
            question="Is this extraction correct?",
            context={"step": "extract", "document_id": "doc-42"},
            options=["Approve", "Reject", "Edit"],
            priority="high",
            deadline=deadline,
        )
        assert req.question == "Is this extraction correct?"
        assert req.context["step"] == "extract"
        assert req.options == ["Approve", "Reject", "Edit"]
        assert req.priority == "high"
        assert req.deadline == deadline
        assert req.workflow_run_id == "run-42"
        assert req.step_name == "extract"

    def test_creation_minimal(self):
        req = HumanReviewRequest(question="Is this OK?")
        assert req.question == "Is this OK?"

    def test_default_priority(self):
        req = HumanReviewRequest(question="Review this")
        assert req.priority == "medium"

    def test_auto_generated_request_id(self):
        req = HumanReviewRequest(question="test")
        assert req.request_id is not None
        assert len(req.request_id) > 0

    def test_priority_levels(self):
        for level in ("low", "medium", "high", "critical"):
            req = HumanReviewRequest(question="test", priority=level)
            assert req.priority == level

    def test_default_options_empty(self):
        req = HumanReviewRequest(question="test")
        assert req.options == []

    def test_default_context_empty(self):
        req = HumanReviewRequest(question="test")
        assert req.context == {}


class TestHumanReviewResponse:
    def test_creation(self):
        resp = HumanReviewResponse(
            decision="Approve",
            reviewer_id="user-123",
        )
        assert resp.decision == "Approve"
        assert resp.reviewer_id == "user-123"

    def test_creation_with_feedback(self):
        resp = HumanReviewResponse(
            decision="Reject",
            reviewer_id="user-456",
            feedback="Extraction missed the date field",
        )
        assert resp.decision == "Reject"
        assert "date field" in resp.feedback

    def test_default_values(self):
        resp = HumanReviewResponse()
        assert resp.decision == ""
        assert resp.feedback == ""
        assert resp.reviewer_id == ""

    def test_resolved_at_auto_set(self):
        resp = HumanReviewResponse(decision="Approve")
        assert resp.resolved_at is not None


class TestHumanLoopManager:
    @pytest.mark.asyncio
    async def test_request_review_raises_error(self):
        manager = HumanLoopManager()
        req = HumanReviewRequest(
            question="Is this correct?",
            options=["Yes", "No"],
            priority="high",
        )
        with pytest.raises(HumanReviewRequiredError):
            await manager.request_review(req)

    @pytest.mark.asyncio
    async def test_raised_error_contains_question(self):
        manager = HumanLoopManager()
        req = HumanReviewRequest(
            question="Approve this output?",
            options=["Approve", "Reject"],
        )
        with pytest.raises(HumanReviewRequiredError) as exc_info:
            await manager.request_review(req)
        assert exc_info.value.question == "Approve this output?"

    @pytest.mark.asyncio
    async def test_pending_count_increases(self):
        manager = HumanLoopManager()
        req = HumanReviewRequest(question="Check this")
        assert manager.pending_count == 0
        try:
            await manager.request_review(req)
        except HumanReviewRequiredError:
            pass
        assert manager.pending_count == 1

    def test_manager_instantiation(self):
        manager = HumanLoopManager()
        assert manager is not None
        assert manager.pending_count == 0
