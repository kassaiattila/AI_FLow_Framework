"""
@test_registry:
    suite: engine-unit
    component: engine.policies
    covers: [src/aiflow/engine/policies.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [engine, retry, circuit-breaker, timeout, policies]
"""
import asyncio
import pytest
from aiflow.engine.policies import RetryPolicy, CircuitBreakerPolicy, CircuitBreakerState, TimeoutPolicy
from aiflow.core.errors import LLMTimeoutError, BudgetExceededError


class TestRetryPolicy:
    def test_default_values(self):
        p = RetryPolicy()
        assert p.max_retries == 3
        assert p.backoff_jitter is True

    def test_should_retry_transient_error(self):
        p = RetryPolicy(max_retries=3)
        assert p.should_retry(LLMTimeoutError("timeout"), attempt=1) is True

    def test_should_not_retry_permanent_error(self):
        p = RetryPolicy(max_retries=3)
        assert p.should_retry(BudgetExceededError("budget"), attempt=1) is False

    def test_should_not_retry_max_attempts(self):
        p = RetryPolicy(max_retries=2)
        assert p.should_retry(LLMTimeoutError("timeout"), attempt=2) is False

    def test_should_retry_named_error(self):
        p = RetryPolicy(max_retries=3, retry_on=["ValueError"])
        assert p.should_retry(ValueError("test"), attempt=1) is True

    def test_should_not_retry_unlisted_error(self):
        p = RetryPolicy(max_retries=3, retry_on=["ValueError"])
        assert p.should_retry(TypeError("test"), attempt=1) is False

    def test_backoff_exponential(self):
        p = RetryPolicy(backoff_base=1.0, backoff_jitter=False)
        assert p.get_delay(0) == 1.0
        assert p.get_delay(1) == 2.0
        assert p.get_delay(2) == 4.0

    def test_backoff_max(self):
        p = RetryPolicy(backoff_base=1.0, backoff_max=10.0, backoff_jitter=False)
        assert p.get_delay(10) == 10.0  # capped

    def test_backoff_with_jitter(self):
        p = RetryPolicy(backoff_base=1.0, backoff_jitter=True)
        delays = [p.get_delay(1) for _ in range(10)]
        assert len(set(round(d, 4) for d in delays)) > 1  # not all the same

    def test_zero_retries(self):
        p = RetryPolicy(max_retries=0)
        assert p.should_retry(LLMTimeoutError("x"), attempt=0) is False


class TestCircuitBreaker:
    def test_closed_allows_calls(self):
        policy = CircuitBreakerPolicy(failure_threshold=3)
        state = CircuitBreakerState()
        assert policy.should_allow(state) is True

    def test_opens_after_threshold(self):
        policy = CircuitBreakerPolicy(failure_threshold=3)
        state = CircuitBreakerState()
        for _ in range(3):
            policy.on_failure(state)
        assert state.state == "open"
        assert policy.should_allow(state) is False

    def test_half_open_after_recovery(self):
        policy = CircuitBreakerPolicy(failure_threshold=2, recovery_timeout=0)
        state = CircuitBreakerState()
        policy.on_failure(state)
        policy.on_failure(state)
        assert state.state == "open"
        # recovery_timeout=0 means immediately half-open
        assert policy.should_allow(state) is True
        assert state.state == "half_open"

    def test_closes_after_half_open_successes(self):
        policy = CircuitBreakerPolicy(failure_threshold=2, recovery_timeout=0, half_open_max_calls=2)
        state = CircuitBreakerState()
        state.state = "half_open"
        policy.on_success(state)
        policy.on_success(state)
        assert state.state == "closed"

    def test_reopens_on_half_open_failure(self):
        policy = CircuitBreakerPolicy(failure_threshold=2, recovery_timeout=0)
        state = CircuitBreakerState()
        state.state = "half_open"
        policy.on_failure(state)
        assert state.state == "open"

    def test_state_reset(self):
        state = CircuitBreakerState()
        state.failure_count = 5
        state.state = "open"
        state.reset()
        assert state.failure_count == 0
        assert state.state == "closed"


class TestTimeoutPolicy:
    @pytest.mark.asyncio
    async def test_executes_within_timeout(self):
        policy = TimeoutPolicy(timeout_seconds=5)
        async def fast():
            return "ok"
        result = await policy.execute_with_timeout(fast())
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self):
        policy = TimeoutPolicy(timeout_seconds=0)
        async def slow():
            await asyncio.sleep(10)
        with pytest.raises(asyncio.TimeoutError):
            await policy.execute_with_timeout(slow())

    @pytest.mark.asyncio
    async def test_skip_on_timeout(self):
        policy = TimeoutPolicy(timeout_seconds=0, on_timeout="skip")
        async def slow():
            await asyncio.sleep(10)
        result = await policy.execute_with_timeout(slow())
        assert result is None
