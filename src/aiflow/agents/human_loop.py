"""Human-in-the-loop integration for the agent system.

When an agent (or a quality gate) determines that human judgement is needed,
a :class:`HumanReviewRequest` is created and the workflow is paused via
:exc:`~aiflow.core.errors.HumanReviewRequiredError`.  A separate process
(e.g. a Slack bot or web UI) later calls :meth:`HumanLoopManager.resolve_review`
to resume execution.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

import structlog

from aiflow.core.errors import HumanReviewRequiredError

__all__ = ["HumanReviewRequest", "HumanReviewResponse", "HumanLoopManager"]

logger = structlog.get_logger(__name__)


class HumanReviewRequest(BaseModel):
    """A request for human review that pauses workflow execution.

    Attributes:
        request_id: Auto-generated unique identifier for this review request.
        workflow_run_id: The ``run_id`` of the workflow that triggered the review.
        step_name: Which agent step requires review.
        question: The question posed to the human reviewer.
        context: Supporting data the reviewer needs to make a decision.
        options: Pre-defined answer choices (if applicable).
        priority: Urgency level (``low`` / ``medium`` / ``high`` / ``critical``).
        deadline: Optional UTC deadline by which the review should be completed.
        created_at: Timestamp of request creation.
    """

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_run_id: str = ""
    step_name: str = ""
    question: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=list)
    priority: str = Field(default="medium")
    deadline: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HumanReviewResponse(BaseModel):
    """A human reviewer's decision that unblocks the paused workflow.

    Attributes:
        request_id: The id of the original :class:`HumanReviewRequest`.
        decision: The chosen option or free-text decision.
        feedback: Optional additional feedback from the reviewer.
        reviewer_id: Identifier of the person who resolved the review.
        resolved_at: Timestamp when the review was completed.
    """

    request_id: str = ""
    decision: str = ""
    feedback: str = ""
    reviewer_id: str = ""
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HumanLoopManager:
    """Manages the lifecycle of human review requests.

    In production this would be backed by a persistent store (e.g. PostgreSQL).
    The in-memory dict used here is intentionally simple -- subclass and
    override the storage methods for real deployments.
    """

    def __init__(self) -> None:
        self._pending: dict[str, HumanReviewRequest] = {}
        self._resolved: dict[str, HumanReviewResponse] = {}

    # ------------------------------------------------------------------
    # Request review
    # ------------------------------------------------------------------

    async def request_review(
        self,
        request: HumanReviewRequest,
    ) -> None:
        """Register a review request and raise to pause the workflow.

        The request is stored internally so it can later be looked up and
        resolved via :meth:`resolve_review`.

        Args:
            request: The review request to submit.

        Raises:
            HumanReviewRequiredError: Always raised to halt the current
                workflow execution until a human responds.
        """
        self._pending[request.request_id] = request
        logger.info(
            "human_review_requested",
            request_id=request.request_id,
            workflow_run_id=request.workflow_run_id,
            step_name=request.step_name,
            priority=request.priority,
        )
        raise HumanReviewRequiredError(
            message=f"Human review required for step '{request.step_name}'",
            question=request.question,
            context=request.context,
            options=request.options or None,
            priority=request.priority,
            deadline_minutes=(
                int((request.deadline - datetime.now(UTC)).total_seconds() / 60)
                if request.deadline
                else None
            ),
        )

    # ------------------------------------------------------------------
    # Resolve review
    # ------------------------------------------------------------------

    async def resolve_review(
        self,
        response: HumanReviewResponse,
    ) -> HumanReviewRequest:
        """Record a human reviewer's decision for a pending request.

        Moves the request from *pending* to *resolved* and returns it so the
        caller can resume the workflow.

        Args:
            response: The reviewer's decision.

        Returns:
            The original :class:`HumanReviewRequest` that was resolved.

        Raises:
            KeyError: If the ``request_id`` is not found in pending reviews.
        """
        request = self._pending.pop(response.request_id)
        self._resolved[response.request_id] = response
        logger.info(
            "human_review_resolved",
            request_id=response.request_id,
            reviewer_id=response.reviewer_id,
            decision=response.decision,
        )
        return request

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def pending_count(self) -> int:
        """Number of reviews still awaiting a human response."""
        return len(self._pending)

    async def get_pending(self, request_id: str) -> HumanReviewRequest | None:
        """Look up a pending review by id (returns ``None`` if not found)."""
        return self._pending.get(request_id)
