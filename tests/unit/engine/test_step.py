"""
@test_registry:
    suite: engine-unit
    component: engine.step
    covers: [src/aiflow/engine/step.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [engine, step, decorator, retry, async]
"""
import asyncio
import pytest
from pydantic import BaseModel
from aiflow.engine.step import step, get_step_definition, is_step, StepDefinition
from aiflow.engine.policies import RetryPolicy
from aiflow.core.errors import LLMTimeoutError


class SampleInput(BaseModel):
    text: str

class SampleOutput(BaseModel):
    result: str
    score: float = 0.0


class TestStepDecorator:
    def test_basic_step(self):
        @step(name="test_step")
        async def my_step(input_data: SampleInput) -> SampleOutput:
            return SampleOutput(result="hello", score=0.9)

        assert is_step(my_step)
        defn = get_step_definition(my_step)
        assert defn is not None
        assert defn.name == "test_step"

    def test_step_with_output_types(self):
        @step(name="typed", output_types={"result": str, "score": float})
        async def my_step(input_data):
            return {"result": "ok", "score": 0.5}

        defn = get_step_definition(my_step)
        assert defn.output_types == {"result": str, "score": float}

    def test_step_with_retry(self):
        @step(name="retryable", retry=RetryPolicy(max_retries=2))
        async def my_step(input_data):
            return {"ok": True}

        defn = get_step_definition(my_step)
        assert defn.retry is not None
        assert defn.retry.max_retries == 2

    def test_step_with_timeout(self):
        @step(name="timed", timeout=30)
        async def my_step(input_data):
            return {"ok": True}

        defn = get_step_definition(my_step)
        assert defn.timeout == 30

    def test_step_type(self):
        @step(name="rpa", step_type="playwright")
        async def my_step(input_data):
            return {}

        defn = get_step_definition(my_step)
        assert defn.step_type == "playwright"

    @pytest.mark.asyncio
    async def test_step_executes(self):
        @step(name="exec_test")
        async def my_step(text: str) -> dict:
            return {"result": text.upper()}

        result = await my_step("hello")
        assert result == {"result": "HELLO"}

    @pytest.mark.asyncio
    async def test_step_retries_on_transient(self):
        call_count = 0

        @step(name="flaky", retry=RetryPolicy(max_retries=3, backoff_base=0.01))
        async def flaky_step() -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMTimeoutError("timeout")
            return {"ok": True}

        result = await flaky_step()
        assert result == {"ok": True}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_step_fails_after_max_retries(self):
        @step(name="always_fail", retry=RetryPolicy(max_retries=1, backoff_base=0.01))
        async def bad_step() -> dict:
            raise LLMTimeoutError("always fails")

        with pytest.raises(LLMTimeoutError):
            await bad_step()

    @pytest.mark.asyncio
    async def test_step_timeout(self):
        @step(name="slow", timeout=1)
        async def slow_step() -> dict:
            await asyncio.sleep(10)
            return {}

        with pytest.raises(asyncio.TimeoutError):
            await slow_step()

    def test_not_a_step(self):
        def regular_function():
            pass
        assert is_step(regular_function) is False
        assert get_step_definition(regular_function) is None

    def test_step_preserves_name(self):
        @step(name="named")
        async def my_function():
            pass
        assert my_function.__name__ == "my_function"
