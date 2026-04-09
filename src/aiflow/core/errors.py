"""AIFlow exception hierarchy.

All errors inherit from AIFlowError with is_transient flag for retry decisions.
Transient errors can be retried; permanent errors require human intervention.
"""

from typing import ClassVar

__all__ = [
    "AIFlowError",
    "TransientError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "ExternalServiceError",
    "PermanentError",
    "BudgetExceededError",
    "QualityGateFailedError",
    "InvalidInputError",
    "WorkflowNotFoundError",
    "AuthorizationError",
    "CircuitBreakerOpenError",
    "HumanReviewRequiredError",
    "ConfigurationError",
]


class AIFlowError(Exception):
    """Base exception for all AIFlow errors."""

    error_code: ClassVar[str] = "AIFLOW_ERROR"
    is_transient: ClassVar[bool] = False
    http_status: ClassVar[int] = 500

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# --- Transient (retryable) ---
class TransientError(AIFlowError):
    is_transient: ClassVar[bool] = True


class LLMTimeoutError(TransientError):
    error_code: ClassVar[str] = "LLM_TIMEOUT"
    http_status: ClassVar[int] = 504


class LLMRateLimitError(TransientError):
    error_code: ClassVar[str] = "LLM_RATE_LIMIT"
    http_status: ClassVar[int] = 429


class ExternalServiceError(TransientError):
    error_code: ClassVar[str] = "EXTERNAL_SERVICE"
    http_status: ClassVar[int] = 502


# --- Permanent (human intervention needed) ---
class PermanentError(AIFlowError):
    is_transient: ClassVar[bool] = False


class BudgetExceededError(PermanentError):
    error_code: ClassVar[str] = "BUDGET_EXCEEDED"
    http_status: ClassVar[int] = 402


class QualityGateFailedError(PermanentError):
    error_code: ClassVar[str] = "QUALITY_GATE_FAILED"
    http_status: ClassVar[int] = 422


class InvalidInputError(PermanentError):
    error_code: ClassVar[str] = "INVALID_INPUT"
    http_status: ClassVar[int] = 400


class WorkflowNotFoundError(PermanentError):
    error_code: ClassVar[str] = "WORKFLOW_NOT_FOUND"
    http_status: ClassVar[int] = 404


class AuthorizationError(PermanentError):
    error_code: ClassVar[str] = "UNAUTHORIZED"
    http_status: ClassVar[int] = 403


class CircuitBreakerOpenError(PermanentError):
    error_code: ClassVar[str] = "CIRCUIT_OPEN"
    http_status: ClassVar[int] = 503


class HumanReviewRequiredError(PermanentError):
    error_code: ClassVar[str] = "HUMAN_REVIEW_REQUIRED"
    http_status: ClassVar[int] = 202

    def __init__(
        self,
        message: str,
        question: str = "",
        context: dict | None = None,
        options: list[str] | None = None,
        priority: str = "medium",
        deadline_minutes: int | None = None,
    ) -> None:
        super().__init__(message)
        self.question = question
        self.context = context or {}
        self.options = options
        self.priority = priority
        self.deadline_minutes = deadline_minutes


class ConfigurationError(PermanentError):
    error_code: ClassVar[str] = "CONFIGURATION_ERROR"
    http_status: ClassVar[int] = 500
