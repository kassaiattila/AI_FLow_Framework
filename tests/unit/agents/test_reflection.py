"""
@test_registry:
    suite: agents-unit
    component: agents.reflection
    covers: [src/aiflow/agents/reflection.py]
    phase: 3
    priority: high
    estimated_duration_ms: 500
    requires_services: []
    tags: [agents, reflection, loop, iteration, quality, async]
"""
import pytest

from aiflow.agents.reflection import ReflectionLoop, ReflectionResult, ReflectionIteration


# --- Test helper callables ---


def _make_generator(outputs: list):
    """Create an async generator that yields outputs in order."""
    call_count = 0

    async def generator(input_data, feedback=None, previous_output=None):
        nonlocal call_count
        result = outputs[min(call_count, len(outputs) - 1)]
        call_count += 1
        return result

    return generator


def _make_critic(scores: list[float], feedbacks: list[str] | None = None):
    """Create an async critic that returns scores in order."""
    call_count = 0
    feedbacks = feedbacks or ["needs improvement"] * len(scores)

    async def critic(output):
        nonlocal call_count
        idx = min(call_count, len(scores) - 1)
        score = scores[idx]
        fb = feedbacks[idx]
        call_count += 1
        return (score, fb)

    return critic


class TestReflectionIteration:
    def test_iteration_record(self):
        record = ReflectionIteration(
            iteration=1,
            output="hello",
            score=0.7,
            feedback="needs more detail",
        )
        assert record.iteration == 1
        assert record.output == "hello"
        assert record.score == 0.7
        assert record.feedback == "needs more detail"

    def test_default_feedback(self):
        record = ReflectionIteration(iteration=1, output="x", score=0.5)
        assert record.feedback == ""


class TestReflectionLoop:
    @pytest.mark.asyncio
    async def test_runs_and_returns_result(self):
        gen = _make_generator(["draft1", "draft2", "draft3"])
        critic = _make_critic([0.5, 0.7, 0.9])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.85,
            max_iterations=5,
        )
        result = await loop.run("initial input")
        assert isinstance(result, ReflectionResult)

    @pytest.mark.asyncio
    async def test_stops_when_quality_threshold_met(self):
        gen = _make_generator(["draft1", "draft2", "draft3"])
        critic = _make_critic([0.5, 0.7, 0.9])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.85,
            max_iterations=10,
        )
        result = await loop.run("input")
        # Should stop at iteration 3 (score 0.9 >= 0.85), not run all 10
        assert result.iterations <= 4
        assert result.final_score >= 0.85

    @pytest.mark.asyncio
    async def test_stops_at_max_iterations(self):
        gen = _make_generator(["d1", "d2", "d3"])
        critic = _make_critic([0.1, 0.2, 0.3])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.99,
            max_iterations=3,
        )
        result = await loop.run("input")
        assert result.iterations == 3
        assert result.final_score < 0.99

    @pytest.mark.asyncio
    async def test_improvement_history_tracked(self):
        gen = _make_generator(["d1", "d2", "d3"])
        critic = _make_critic([0.3, 0.6, 0.9], ["bad", "ok", "good"])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.85,
            max_iterations=5,
        )
        result = await loop.run("input")
        assert len(result.improvement_history) >= 2
        # Check that scores are recorded in history
        scores = [h.score for h in result.improvement_history]
        assert scores == pytest.approx([0.3, 0.6, 0.9])

    @pytest.mark.asyncio
    async def test_single_iteration_if_already_good(self):
        gen = _make_generator(["perfect_output"])
        critic = _make_critic([0.95])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.8,
            max_iterations=5,
        )
        result = await loop.run("input")
        assert result.iterations == 1
        assert result.final_score >= 0.8

    @pytest.mark.asyncio
    async def test_result_contains_final_output(self):
        gen = _make_generator(["final_answer"])
        critic = _make_critic([0.9])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.8,
            max_iterations=3,
        )
        result = await loop.run("input")
        assert result.final_output == "final_answer"

    @pytest.mark.asyncio
    async def test_history_iteration_numbers_are_sequential(self):
        gen = _make_generator(["a", "b"])
        critic = _make_critic([0.4, 0.9])
        loop = ReflectionLoop(
            generator=gen,
            critic=critic,
            quality_threshold=0.85,
            max_iterations=5,
        )
        result = await loop.run("input")
        iteration_numbers = [h.iteration for h in result.improvement_history]
        assert iteration_numbers == [1, 2]
