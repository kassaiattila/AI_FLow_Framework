"""AIFlow core kernel - config, context, errors, events, DI, registry."""

from aiflow.core.config import AIFlowSettings, get_settings
from aiflow.core.context import ExecutionContext, TraceContext
from aiflow.core.di import Container
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
from aiflow.core.events import EventBus, event_bus
from aiflow.core.registry import Registry
from aiflow.core.types import (
    Priority,
    SkillType,
    Status,
    StepResult,
    StepStatus,
    WorkflowResult,
)

__all__ = [
    # Config
    "AIFlowSettings",
    "get_settings",
    # Context
    "ExecutionContext",
    "TraceContext",
    # DI
    "Container",
    # Errors
    "AIFlowError",
    "AuthorizationError",
    "BudgetExceededError",
    "CircuitBreakerOpenError",
    "ConfigurationError",
    "ExternalServiceError",
    "HumanReviewRequiredError",
    "InvalidInputError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "PermanentError",
    "QualityGateFailedError",
    "TransientError",
    "WorkflowNotFoundError",
    # Events
    "EventBus",
    "event_bus",
    # Registry
    "Registry",
    # Types
    "Priority",
    "SkillType",
    "Status",
    "StepResult",
    "StepStatus",
    "WorkflowResult",
]
