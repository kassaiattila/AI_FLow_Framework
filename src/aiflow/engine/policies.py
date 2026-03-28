"""Resilience policies for step execution: retry, circuit breaker, timeout.

RetryPolicy is modeled after LangGraph's RetryPolicy (validated match).
"""
import asyncio
import random
import time
from typing import Callable

from pydantic import BaseModel, Field

import structlog

__all__ = ["RetryPolicy", "CircuitBreakerPolicy", "TimeoutPolicy", "CircuitBreakerState"]

logger = structlog.get_logger(__name__)


class RetryPolicy(BaseModel):
    """Exponential backoff retry policy with jitter.

    Inspired by LangGraph RetryPolicy (1:1 pattern match).
    Only retries on transient errors by default.
    """
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    backoff_jitter: bool = True
    retry_on: list[str] = Field(default_factory=lambda: [
        "LLMTimeoutError", "LLMRateLimitError", "ExternalServiceError",
        "TimeoutError", "ConnectionError",
    ])

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if the error should be retried."""
        if attempt >= self.max_retries:
            return False
        error_name = type(error).__name__
        # Also check is_transient attribute (AIFlowError hierarchy)
        if hasattr(error, 'is_transient') and error.is_transient:
            return True
        return error_name in self.retry_on

    def get_delay(self, attempt: int) -> float:
        """Calculate backoff delay for given attempt (0-indexed)."""
        delay = min(self.backoff_base * (2 ** attempt), self.backoff_max)
        if self.backoff_jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


class CircuitBreakerState:
    """Tracks circuit breaker state (in-memory, Redis-backed in production)."""

    def __init__(self) -> None:
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0
        self.state: str = "closed"  # closed, open, half_open
        self.half_open_successes: int = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

    def record_success(self) -> None:
        if self.state == "half_open":
            self.half_open_successes += 1
        self.failure_count = 0

    def reset(self) -> None:
        self.failure_count = 0
        self.state = "closed"
        self.half_open_successes = 0


class CircuitBreakerPolicy(BaseModel):
    """Circuit breaker pattern - stops calling a failing service."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds before trying half-open
    half_open_max_calls: int = 3  # successful calls to close circuit

    def should_allow(self, state: CircuitBreakerState) -> bool:
        """Check if the call should be allowed."""
        if state.state == "closed":
            return True
        if state.state == "open":
            elapsed = time.monotonic() - state.last_failure_time
            if elapsed >= self.recovery_timeout:
                state.state = "half_open"
                state.half_open_successes = 0
                logger.info("circuit_breaker_half_open")
                return True
            return False
        if state.state == "half_open":
            return True
        return False

    def on_success(self, state: CircuitBreakerState) -> None:
        """Record a successful call."""
        state.record_success()
        if state.state == "half_open" and state.half_open_successes >= self.half_open_max_calls:
            state.reset()
            logger.info("circuit_breaker_closed")

    def on_failure(self, state: CircuitBreakerState) -> None:
        """Record a failed call."""
        state.record_failure()
        if state.state == "half_open":
            state.state = "open"
            logger.warning("circuit_breaker_reopened")
        elif state.failure_count >= self.failure_threshold:
            state.state = "open"
            logger.warning("circuit_breaker_opened", failures=state.failure_count)


class TimeoutPolicy(BaseModel):
    """Timeout policy for step execution."""
    timeout_seconds: int = 60
    on_timeout: str = "fail"  # fail | skip | fallback
    fallback_step: str | None = None

    async def execute_with_timeout(self, coro):
        """Execute a coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("step_timeout", timeout=self.timeout_seconds, action=self.on_timeout)
            if self.on_timeout == "skip":
                return None
            raise
