"""
@test_registry:
    suite: service-unit
    component: services.resilience
    covers: [src/aiflow/services/resilience/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [service, resilience, circuit-breaker, retry]
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from aiflow.services.resilience.service import (
    CircuitState,
    ResilienceConfig,
    ResilienceRule,
    ResilienceService,
)


@pytest.fixture()
def svc() -> ResilienceService:
    """Resilience service with a fast test rule."""
    config = ResilienceConfig(
        rules=[
            ResilienceRule(
                key="test",
                max_retries=2,
                retry_delay_seconds=0.01,
                retry_backoff_factor=1.0,
                retry_max_delay_seconds=0.1,
                retryable_exceptions=["ConnectionError"],
                circuit_failure_threshold=3,
                circuit_recovery_timeout_seconds=0.05,
                circuit_half_open_max_calls=1,
            )
        ]
    )
    return ResilienceService(config=config)


class TestResilienceService:
    @pytest.mark.asyncio
    async def test_execute_success(self, svc: ResilienceService) -> None:
        """Successful function returns its result."""
        func = AsyncMock(return_value=42)
        result = await svc.execute("test", func)
        assert result == 42
        func.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_retry_on_failure(self, svc: ResilienceService) -> None:
        """Transient error triggers retry, then succeeds."""
        func = AsyncMock(side_effect=[ConnectionError("fail"), "ok"])
        result = await svc.execute("test", func)
        assert result == "ok"
        assert func.await_count == 2

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self) -> None:
        """Repeated failures open the circuit breaker.

        Sprint O FU-5 — unquarantined after the Clock seam landed in
        ``ResilienceService.__init__(clock=...)``. The fixture pins the
        breaker's clock at t=0 so the OPEN→HALF_OPEN recovery window
        (50 ms) cannot elapse mid-loop under full-suite load — that was
        the original flake source (see ``docs/quarantine.md``).
        """
        from aiflow.core.errors import CircuitBreakerOpenError

        # Pinned clock: every breaker call sees t=0.0, so recovery
        # timeout (0.05s) can never elapse. Deterministic.
        svc = ResilienceService(
            config=ResilienceConfig(
                rules=[
                    ResilienceRule(
                        key="test",
                        max_retries=2,
                        retry_delay_seconds=0.01,
                        retry_backoff_factor=1.0,
                        retry_max_delay_seconds=0.1,
                        retryable_exceptions=["ConnectionError"],
                        circuit_failure_threshold=3,
                        circuit_recovery_timeout_seconds=0.05,
                        circuit_half_open_max_calls=1,
                    )
                ]
            ),
            clock=lambda: 0.0,
        )

        fail_func = AsyncMock(side_effect=ValueError("permanent"))

        # Exhaust retries 3 times to hit threshold (3 failures)
        for _ in range(3):
            with pytest.raises(ValueError, match="permanent"):
                await svc.execute("test", fail_func)

        state = svc.get_circuit_state("test")
        assert state["state"] == CircuitState.OPEN.value

        # Next call should be rejected immediately — pinned clock guarantees
        # the recovery window has not elapsed.
        with pytest.raises(CircuitBreakerOpenError):
            await svc.execute("test", AsyncMock())

    @pytest.mark.asyncio
    async def test_circuit_half_open_recovery(self, svc: ResilienceService) -> None:
        """After recovery timeout, circuit goes half-open then closed on success."""

        fail_func = AsyncMock(side_effect=ValueError("fail"))
        for _ in range(3):
            with pytest.raises(ValueError):
                await svc.execute("test", fail_func)

        # Wait for recovery timeout
        await asyncio.sleep(0.06)

        # Next call in half-open state should succeed
        success_func = AsyncMock(return_value="recovered")
        result = await svc.execute("test", success_func)
        assert result == "recovered"

        state = svc.get_circuit_state("test")
        assert state["state"] == CircuitState.CLOSED.value

    def test_get_circuit_state(self, svc: ResilienceService) -> None:
        """get_circuit_state returns correct structure."""
        state = svc.get_circuit_state("test")
        assert state["key"] == "test"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["threshold"] == 3
