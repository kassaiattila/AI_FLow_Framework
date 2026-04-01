"""Resilience service — centralized retry and circuit breaker for external calls.

Provides retry with exponential backoff and circuit breaker pattern.
Configurable per-service (e.g., different settings for LLM vs email vs DB).
"""
from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog
from pydantic import Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "CircuitState",
    "ResilienceConfig",
    "ResilienceRule",
    "ResilienceService",
]

logger = structlog.get_logger(__name__)
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class ResilienceRule(ServiceConfig):
    """Resilience configuration for a specific service/operation."""

    key: str = "default"
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_factor: float = 2.0
    retry_max_delay_seconds: float = 30.0
    retryable_exceptions: list[str] = Field(
        default_factory=lambda: ["TimeoutError", "ConnectionError"]
    )
    # Circuit breaker settings
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout_seconds: float = 30.0
    circuit_half_open_max_calls: int = 1


class ResilienceConfig(ServiceConfig):
    """Resilience service configuration."""

    rules: list[ResilienceRule] = Field(default_factory=list)


class _CircuitBreaker:
    """Internal circuit breaker state for a single key."""

    def __init__(self, rule: ResilienceRule) -> None:
        self.rule = rule
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.rule.circuit_failure_threshold:
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.rule.circuit_recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        # HALF_OPEN
        if self.half_open_calls < self.rule.circuit_half_open_max_calls:
            self.half_open_calls += 1
            return True
        return False


class ResilienceService(BaseService):
    """Centralized retry + circuit breaker for external service calls."""

    def __init__(self, config: ResilienceConfig | None = None) -> None:
        self._res_config = config or ResilienceConfig()
        super().__init__(self._res_config)
        self._rules: dict[str, ResilienceRule] = {
            r.key: r for r in self._res_config.rules
        }
        self._breakers: dict[str, _CircuitBreaker] = {}

    @property
    def service_name(self) -> str:
        return "resilience"

    @property
    def service_description(self) -> str:
        return "Centralized retry and circuit breaker for external calls"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        self._breakers.clear()

    async def health_check(self) -> bool:
        return True

    def _get_rule(self, key: str) -> ResilienceRule:
        return self._rules.get(key, ResilienceRule(key=key))

    def _get_breaker(self, key: str) -> _CircuitBreaker:
        if key not in self._breakers:
            self._breakers[key] = _CircuitBreaker(self._get_rule(key))
        return self._breakers[key]

    async def execute(
        self,
        key: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with retry + circuit breaker protection.

        Args:
            key: Service/operation identifier for rule lookup.
            func: Async callable to execute.
            *args, **kwargs: Arguments passed to func.

        Returns:
            The result of func(*args, **kwargs).

        Raises:
            CircuitBreakerOpenError: If circuit is open.
            The original exception if all retries exhausted.
        """
        breaker = self._get_breaker(key)
        rule = self._get_rule(key)

        if not breaker.can_execute():
            from aiflow.core.errors import CircuitBreakerOpenError

            self._logger.warning(
                "circuit_breaker_open",
                key=key,
                failures=breaker.failure_count,
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker open for '{key}' "
                f"(failures: {breaker.failure_count})"
            )

        last_error: Exception | None = None
        delay = rule.retry_delay_seconds

        for attempt in range(rule.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                if attempt > 0:
                    self._logger.info(
                        "retry_succeeded", key=key, attempt=attempt + 1
                    )
                return result
            except Exception as exc:
                last_error = exc
                exc_name = type(exc).__name__
                is_retryable = exc_name in rule.retryable_exceptions

                if not is_retryable or attempt >= rule.max_retries:
                    breaker.record_failure()
                    self._logger.warning(
                        "call_failed",
                        key=key,
                        attempt=attempt + 1,
                        error=str(exc),
                        retryable=is_retryable,
                    )
                    break

                self._logger.debug(
                    "retrying",
                    key=key,
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
                delay = min(
                    delay * rule.retry_backoff_factor,
                    rule.retry_max_delay_seconds,
                )

        raise last_error  # type: ignore[misc]

    def get_circuit_state(self, key: str) -> dict[str, Any]:
        """Get circuit breaker state for a key."""
        breaker = self._get_breaker(key)
        return {
            "key": key,
            "state": breaker.state.value,
            "failure_count": breaker.failure_count,
            "threshold": breaker.rule.circuit_failure_threshold,
        }

    def reset_circuit(self, key: str) -> None:
        """Manually reset circuit breaker for a key."""
        if key in self._breakers:
            self._breakers[key].record_success()
            self._logger.info("circuit_reset", key=key)

    def add_rule(self, rule: ResilienceRule) -> None:
        """Add or update a resilience rule at runtime."""
        self._rules[rule.key] = rule
        if rule.key in self._breakers:
            self._breakers[rule.key].rule = rule
