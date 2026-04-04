"""
@test_registry:
    suite: core-unit
    component: core.errors
    covers: [src/aiflow/core/errors.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [errors, exceptions, hierarchy]
"""
import pytest

from aiflow.core.errors import (
    AIFlowError,
    AuthorizationError,
    BudgetExceededError,
    CircuitBreakerOpenError,
    ConfigurationError,
    ExternalServiceError,
    HumanReviewRequiredError,
    InvalidInputError,
    LLMRateLimitError,
    LLMTimeoutError,
    PermanentError,
    QualityGateFailedError,
    TransientError,
    WorkflowNotFoundError,
)


class TestErrorHierarchy:
    def test_all_errors_inherit_from_aiflow_error(self):
        errors = [
            LLMTimeoutError, LLMRateLimitError, ExternalServiceError,
            BudgetExceededError, QualityGateFailedError, InvalidInputError,
            WorkflowNotFoundError, AuthorizationError, CircuitBreakerOpenError,
            HumanReviewRequiredError, ConfigurationError,
        ]
        for error_cls in errors:
            assert issubclass(error_cls, AIFlowError)

    def test_transient_errors_are_transient(self):
        transient = [LLMTimeoutError, LLMRateLimitError, ExternalServiceError]
        for error_cls in transient:
            assert error_cls.is_transient is True
            assert issubclass(error_cls, TransientError)

    def test_permanent_errors_are_not_transient(self):
        permanent = [BudgetExceededError, QualityGateFailedError, InvalidInputError,
                     WorkflowNotFoundError, AuthorizationError]
        for error_cls in permanent:
            assert error_cls.is_transient is False
            assert issubclass(error_cls, PermanentError)


class TestErrorAttributes:
    def test_error_message(self):
        err = LLMTimeoutError("Request timed out")
        assert str(err) == "Request timed out"
        assert err.message == "Request timed out"

    def test_error_details(self):
        err = InvalidInputError("Bad input", details={"field": "name"})
        assert err.details == {"field": "name"}

    def test_error_code(self):
        assert LLMTimeoutError.error_code == "LLM_TIMEOUT"
        assert BudgetExceededError.error_code == "BUDGET_EXCEEDED"
        assert InvalidInputError.error_code == "INVALID_INPUT"

    def test_http_status(self):
        assert LLMTimeoutError.http_status == 504
        assert LLMRateLimitError.http_status == 429
        assert BudgetExceededError.http_status == 402
        assert InvalidInputError.http_status == 400
        assert WorkflowNotFoundError.http_status == 404
        assert AuthorizationError.http_status == 403


class TestHumanReviewRequiredError:
    def test_human_review_with_all_fields(self):
        err = HumanReviewRequiredError(
            message="Review needed",
            question="Is this extraction correct?",
            context={"step": "extract"},
            options=["Approve", "Reject"],
            priority="high",
            deadline_minutes=60,
        )
        assert err.question == "Is this extraction correct?"
        assert err.options == ["Approve", "Reject"]
        assert err.priority == "high"
        assert err.deadline_minutes == 60
        assert err.http_status == 202

    def test_human_review_defaults(self):
        err = HumanReviewRequiredError("Review needed")
        assert err.question == ""
        assert err.options is None
        assert err.priority == "medium"


class TestErrorCatching:
    def test_catch_transient(self):
        with pytest.raises(TransientError):
            raise LLMTimeoutError("timeout")

    def test_catch_permanent(self):
        with pytest.raises(PermanentError):
            raise BudgetExceededError("budget exceeded")

    def test_catch_aiflow_error(self):
        with pytest.raises(AIFlowError):
            raise LLMRateLimitError("rate limited")
