"""AIFlow exception hierarchy.

All errors inherit from AIFlowError with is_transient flag for retry decisions.
Transient errors can be retried; permanent errors require human intervention.
"""

from typing import Any, ClassVar

__all__ = [
    "AIFlowError",
    "TransientError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "ExternalServiceError",
    "PermanentError",
    "BudgetExceededError",
    "CostCapBreached",
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

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
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


class CostCapBreached(PermanentError):  # noqa: N818 — semantic name preserved for ExternalAPI/docs
    """Raised when a tenant's running cost exceeds its configured cap.

    Mapped to HTTP 429 so clients back off rather than retrying instantly.
    Carries ``tenant_id``, ``cap_usd``, ``current_usd``, and ``window_h`` in
    ``details`` for observability and UI rendering.
    """

    error_code: ClassVar[str] = "COST_CAP_BREACHED"
    http_status: ClassVar[int] = 429

    def __init__(
        self,
        tenant_id: str,
        cap_usd: float,
        current_usd: float,
        window_h: int,
    ) -> None:
        super().__init__(
            f"Cost cap breached for tenant {tenant_id!r}: "
            f"${current_usd:.6f} >= ${cap_usd:.6f} over {window_h}h window.",
            details={
                "tenant_id": tenant_id,
                "cap_usd": cap_usd,
                "current_usd": current_usd,
                "window_h": window_h,
            },
        )
        self.tenant_id = tenant_id
        self.cap_usd = cap_usd
        self.current_usd = current_usd
        self.window_h = window_h


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
        context: dict[str, Any] | None = None,
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
