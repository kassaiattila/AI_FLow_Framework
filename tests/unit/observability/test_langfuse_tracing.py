"""
@test_registry:
    suite: core-unit
    component: observability.tracing.langfuse
    covers: [src/aiflow/observability/tracing.py]
    phase: v1.2.1-S7
    priority: high
    estimated_duration_ms: 500
    requires_services: []
    tags: [observability, langfuse, tracing, decorator]
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aiflow.observability.tracing import (
    LangfuseTracer,
    TraceManager,
    get_langfuse_client,
    trace_llm_call,
)


class TestLangfuseTracerDisabled:
    """Verify LangfuseTracer works when Langfuse is disabled/unconfigured."""

    def test_init_without_keys(self):
        tracer = LangfuseTracer(public_key=None, secret_key=None, enabled=False)
        assert not tracer.connected

    def test_init_disabled_flag(self):
        tracer = LangfuseTracer(public_key="pk-test", secret_key="sk-test", enabled=False)
        assert not tracer.connected

    @pytest.mark.asyncio
    async def test_create_trace_returns_id_when_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        trace_id = await tracer.create_trace("test", {})
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0

    @pytest.mark.asyncio
    async def test_create_span_returns_id_when_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        trace_id = await tracer.create_trace("test", {})
        span_id = await tracer.create_span(trace_id, "step-1")
        assert isinstance(span_id, str)

    @pytest.mark.asyncio
    async def test_finish_span_noop_when_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        trace_id = await tracer.create_trace("test", {})
        span_id = await tracer.create_span(trace_id, "step-1")
        await tracer.finish_span(trace_id, span_id)

    @pytest.mark.asyncio
    async def test_finish_trace_noop_when_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        trace_id = await tracer.create_trace("test", {})
        await tracer.finish_trace(trace_id)

    @pytest.mark.asyncio
    async def test_get_trace_returns_none(self):
        tracer = LangfuseTracer(enabled=False)
        result = await tracer.get_trace("some-id")
        assert result is None

    def test_score_noop_when_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        tracer.score(trace_id="t1", name="accuracy", value=0.95)

    def test_generation_noop_when_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        tracer.generation(trace_id="t1", name="gen", model="gpt-4o")

    @pytest.mark.asyncio
    async def test_check_health_disabled(self):
        tracer = LangfuseTracer(enabled=False)
        health = await tracer.check_health()
        assert health["status"] == "disabled"


class TestLangfuseTracerConnected:
    """Verify LangfuseTracer calls real Langfuse SDK when available."""

    @pytest.fixture
    def mock_langfuse_class(self):
        with patch("aiflow.observability.tracing.Langfuse", create=True) as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            yield mock_cls, mock_client

    def _make_tracer(self, mock_langfuse_class):
        mock_cls, mock_client = mock_langfuse_class
        with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_cls)}):
            tracer = LangfuseTracer.__new__(LangfuseTracer)
            tracer._public_key = "pk-test"
            tracer._secret_key = "sk-test"
            tracer._host = "https://cloud.langfuse.com"
            tracer._enabled = True
            tracer._client = mock_client
            tracer._traces = {}
            tracer._spans = {}
            return tracer, mock_client

    @pytest.mark.asyncio
    async def test_create_trace_calls_sdk(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace

        trace_id = await tracer.create_trace("pipeline:test", {"key": "val"})
        assert isinstance(trace_id, str)
        mock_client.trace.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_span_calls_sdk(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace
        mock_span = MagicMock()
        mock_trace.span.return_value = mock_span

        trace_id = await tracer.create_trace("test", {})
        span_id = await tracer.create_span(trace_id, "step-1", {"idx": 0})
        assert isinstance(span_id, str)
        mock_trace.span.assert_called_once()

    @pytest.mark.asyncio
    async def test_finish_span_calls_end(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace
        mock_span = MagicMock()
        mock_trace.span.return_value = mock_span

        trace_id = await tracer.create_trace("test", {})
        span_id = await tracer.create_span(trace_id, "step-1")
        await tracer.finish_span(trace_id, span_id, {"status": "completed"})
        mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_finish_trace_flushes(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace

        trace_id = await tracer.create_trace("test", {})
        await tracer.finish_trace(trace_id, {"status": "completed"})
        mock_client.flush.assert_called()

    def test_score_calls_sdk(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        tracer.score(trace_id="t1", name="accuracy", value=0.95, comment="good")
        mock_client.score.assert_called_once_with(
            trace_id="t1", name="accuracy", value=0.95, comment="good"
        )

    def test_generation_calls_sdk(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace
        tracer._traces["t1"] = mock_trace

        tracer.generation(
            trace_id="t1", name="classify", model="gpt-4o",
            input_data="hello", output_data="world",
            usage={"input": 10, "output": 5},
        )
        mock_trace.generation.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_ok(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_client.auth_check.return_value = True
        health = await tracer.check_health()
        assert health["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_health_auth_fail(self, mock_langfuse_class):
        tracer, mock_client = self._make_tracer(mock_langfuse_class)
        mock_client.auth_check.return_value = False
        health = await tracer.check_health()
        assert health["status"] == "error"


class TestTraceLlmCallDecorator:
    """Verify the @trace_llm_call decorator."""

    @pytest.mark.asyncio
    async def test_decorator_passthrough_without_client(self):
        """When no Langfuse client, function runs normally."""

        @trace_llm_call(name="test.func")
        async def my_func(x: int) -> int:
            return x * 2

        # Ensure no global client
        import aiflow.observability.tracing as mod
        original = mod._langfuse_client
        mod._langfuse_client = None
        try:
            result = await my_func(5)
            assert result == 10
        finally:
            mod._langfuse_client = original

    @pytest.mark.asyncio
    async def test_decorator_traces_with_client(self):
        """When Langfuse client exists, function is traced."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace

        @trace_llm_call(name="test.traced")
        async def my_func(x: int) -> dict:
            return {"result": x * 3}

        import aiflow.observability.tracing as mod
        original = mod._langfuse_client
        mod._langfuse_client = mock_client
        try:
            result = await my_func(4)
            assert result == {"result": 12}
            mock_client.trace.assert_called_once()
            mock_trace.update.assert_called_once()
            mock_client.flush.assert_called()
        finally:
            mod._langfuse_client = original

    @pytest.mark.asyncio
    async def test_decorator_handles_exception(self):
        """When function raises, error is recorded in trace."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace

        @trace_llm_call(name="test.error")
        async def my_func() -> None:
            raise ValueError("test error")

        import aiflow.observability.tracing as mod
        original = mod._langfuse_client
        mod._langfuse_client = mock_client
        try:
            with pytest.raises(ValueError, match="test error"):
                await my_func()
            mock_trace.update.assert_called_once()
            # Verify error was captured in metadata
            call_kwargs = mock_trace.update.call_args[1]
            assert "error" in call_kwargs.get("metadata", {})
        finally:
            mod._langfuse_client = original

    @pytest.mark.asyncio
    async def test_decorator_auto_names(self):
        """When no name given, uses module.qualname."""

        @trace_llm_call()
        async def auto_named() -> str:
            return "ok"

        import aiflow.observability.tracing as mod
        original = mod._langfuse_client
        mod._langfuse_client = None
        try:
            result = await auto_named()
            assert result == "ok"
        finally:
            mod._langfuse_client = original


class TestTraceManagerWithLangfuse:
    """Verify TraceManager works with LangfuseTracer backend."""

    @pytest.mark.asyncio
    async def test_manager_with_disabled_langfuse(self):
        tracer = LangfuseTracer(enabled=False)
        manager = TraceManager(backend=tracer)
        trace_id = await manager.start_trace("test")
        assert isinstance(trace_id, str)
        span_id = await manager.start_span(trace_id, "step-1")
        assert isinstance(span_id, str)
        await manager.end_span(trace_id, span_id)
        await manager.end_trace(trace_id)

    def test_manager_backend_property(self):
        tracer = LangfuseTracer(enabled=False)
        manager = TraceManager(backend=tracer)
        assert manager.backend is tracer
