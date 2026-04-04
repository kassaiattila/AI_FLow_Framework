"""
@test_registry:
    suite: core-unit
    component: observability.tracing
    covers: [src/aiflow/observability/tracing.py]
    phase: 6
    priority: high
    estimated_duration_ms: 300
    requires_services: []
    tags: [observability, tracing, spans, otel]
"""

import pytest

from aiflow.observability.tracing import InMemoryTracer, TraceManager


class TestInMemoryTracer:
    """Verify InMemoryTracer records traces and spans correctly."""

    @pytest.fixture
    def tracer(self):
        return InMemoryTracer()

    @pytest.mark.asyncio
    async def test_create_trace_returns_trace_id(self, tracer):
        trace_id = await tracer.create_trace(name="test-workflow", metadata={})
        assert trace_id is not None
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0

    @pytest.mark.asyncio
    async def test_create_span_returns_span_id(self, tracer):
        trace_id = await tracer.create_trace(name="wf", metadata={})
        span_id = await tracer.create_span(trace_id=trace_id, name="step-1")
        assert span_id is not None
        assert isinstance(span_id, str)
        assert len(span_id) > 0

    @pytest.mark.asyncio
    async def test_finish_span(self, tracer):
        trace_id = await tracer.create_trace(name="wf", metadata={})
        span_id = await tracer.create_span(trace_id=trace_id, name="step-1")
        # Should not raise
        await tracer.finish_span(trace_id=trace_id, span_id=span_id)
        trace = await tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.spans[span_id].status == "completed"

    @pytest.mark.asyncio
    async def test_finish_trace(self, tracer):
        trace_id = await tracer.create_trace(name="wf", metadata={})
        await tracer.finish_trace(trace_id=trace_id)
        trace = await tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.status == "completed"
        assert trace.ended_at is not None

    @pytest.mark.asyncio
    async def test_trace_contains_spans(self, tracer):
        trace_id = await tracer.create_trace(name="wf", metadata={})
        span_a = await tracer.create_span(trace_id=trace_id, name="step-a")
        span_b = await tracer.create_span(trace_id=trace_id, name="step-b")
        await tracer.finish_span(trace_id=trace_id, span_id=span_a)
        await tracer.finish_span(trace_id=trace_id, span_id=span_b)
        await tracer.finish_trace(trace_id=trace_id)

        trace = await tracer.get_trace(trace_id)
        assert trace is not None
        assert len(trace.spans) == 2

    @pytest.mark.asyncio
    async def test_multiple_traces_tracked_independently(self, tracer):
        t1 = await tracer.create_trace(name="workflow-a", metadata={})
        t2 = await tracer.create_trace(name="workflow-b", metadata={})

        await tracer.create_span(trace_id=t1, name="span-a1")
        await tracer.create_span(trace_id=t2, name="span-b1")
        await tracer.create_span(trace_id=t2, name="span-b2")

        trace1 = await tracer.get_trace(t1)
        trace2 = await tracer.get_trace(t2)

        assert trace1 is not None
        assert trace2 is not None
        assert len(trace1.spans) == 1
        assert len(trace2.spans) == 2

    @pytest.mark.asyncio
    async def test_span_stores_name(self, tracer):
        trace_id = await tracer.create_trace(name="wf", metadata={})
        span_id = await tracer.create_span(trace_id=trace_id, name="my-step")
        await tracer.finish_span(trace_id=trace_id, span_id=span_id)

        trace = await tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.spans[span_id].name == "my-step"

    @pytest.mark.asyncio
    async def test_get_trace_returns_none_for_unknown(self, tracer):
        result = await tracer.get_trace("nonexistent-id")
        assert result is None


class TestTraceManager:
    """Verify TraceManager delegates to the configured tracer backend."""

    def test_create_with_in_memory_backend(self):
        tracer = InMemoryTracer()
        manager = TraceManager(backend=tracer)
        assert manager is not None

    @pytest.mark.asyncio
    async def test_manager_start_trace(self):
        tracer = InMemoryTracer()
        manager = TraceManager(backend=tracer)
        trace_id = await manager.start_trace(name="managed-wf")
        assert trace_id is not None
        assert isinstance(trace_id, str)
        # Verify it landed in the backend
        trace = await tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.name == "managed-wf"
