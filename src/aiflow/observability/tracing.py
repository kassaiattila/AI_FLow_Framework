"""Tracing abstraction - pluggable trace/span management.

Provides:
    - TraceManager: high-level API to start/end traces and spans
    - InMemoryTracer: in-memory implementation for testing
    - LangfuseTracer: real Langfuse integration with graceful fallback
    - trace_llm_call: decorator for automatic LLM call tracing

Usage:
    from aiflow.observability.tracing import TraceManager, LangfuseTracer
    backend = LangfuseTracer(public_key="pk-...", secret_key="sk-...", host="https://cloud.langfuse.com")
    manager = TraceManager(backend)
    trace_id = await manager.start_trace("my-workflow", {"user": "abc"})
    span_id = await manager.start_span(trace_id, "step-1")
    await manager.end_span(trace_id, span_id)
    await manager.end_trace(trace_id)
"""

from __future__ import annotations

import functools
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "SpanRecord",
    "TraceRecord",
    "TracerBackend",
    "InMemoryTracer",
    "LangfuseTracer",
    "TraceManager",
    "trace_llm_call",
    "get_langfuse_client",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SpanRecord(BaseModel):
    """A single span within a trace."""

    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    name: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "running"


class TraceRecord(BaseModel):
    """A complete trace containing one or more spans."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    spans: dict[str, SpanRecord] = Field(default_factory=dict)
    status: str = "running"


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------

class TracerBackend(ABC):
    """Abstract tracing backend interface."""

    @abstractmethod
    async def create_trace(self, name: str, metadata: dict[str, Any]) -> str:
        """Create a new trace and return its ID."""

    @abstractmethod
    async def create_span(self, trace_id: str, name: str, metadata: dict[str, Any] | None = None) -> str:
        """Create a span within a trace and return its ID."""

    @abstractmethod
    async def finish_span(self, trace_id: str, span_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Mark a span as completed."""

    @abstractmethod
    async def finish_trace(self, trace_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Mark a trace as completed."""

    @abstractmethod
    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Retrieve a trace by ID."""


# ---------------------------------------------------------------------------
# In-memory implementation (testing / local dev)
# ---------------------------------------------------------------------------

class InMemoryTracer(TracerBackend):
    """In-memory tracer that stores traces in a dict. Ideal for tests."""

    def __init__(self) -> None:
        self._traces: dict[str, TraceRecord] = {}

    async def create_trace(self, name: str, metadata: dict[str, Any]) -> str:
        trace = TraceRecord(name=name, metadata=metadata)
        self._traces[trace.trace_id] = trace
        logger.debug("trace_created", trace_id=trace.trace_id, name=name)
        return trace.trace_id

    async def create_span(self, trace_id: str, name: str, metadata: dict[str, Any] | None = None) -> str:
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace '{trace_id}' not found")
        span = SpanRecord(trace_id=trace_id, name=name, metadata=metadata or {})
        trace.spans[span.span_id] = span
        logger.debug("span_created", trace_id=trace_id, span_id=span.span_id, name=name)
        return span.span_id

    async def finish_span(self, trace_id: str, span_id: str, metadata: dict[str, Any] | None = None) -> None:
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace '{trace_id}' not found")
        span = trace.spans.get(span_id)
        if span is None:
            raise ValueError(f"Span '{span_id}' not found in trace '{trace_id}'")
        span.ended_at = datetime.now(timezone.utc)
        span.status = "completed"
        if metadata:
            span.metadata.update(metadata)
        logger.debug("span_finished", trace_id=trace_id, span_id=span_id)

    async def finish_trace(self, trace_id: str, metadata: dict[str, Any] | None = None) -> None:
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace '{trace_id}' not found")
        trace.ended_at = datetime.now(timezone.utc)
        trace.status = "completed"
        if metadata:
            trace.metadata.update(metadata)
        logger.debug("trace_finished", trace_id=trace_id)

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        return self._traces.get(trace_id)

    @property
    def traces(self) -> dict[str, TraceRecord]:
        """Access raw trace storage (test helper)."""
        return self._traces


# ---------------------------------------------------------------------------
# Langfuse real implementation (with graceful fallback)
# ---------------------------------------------------------------------------

# Module-level singleton for the Langfuse client
_langfuse_client: Any = None
_langfuse_available: bool | None = None


def get_langfuse_client() -> Any:
    """Return the global Langfuse client, or None if unavailable."""
    return _langfuse_client


class LangfuseTracer(TracerBackend):
    """Langfuse-backed tracer using the ``langfuse`` SDK.

    Creates real traces and spans in Langfuse when configured.
    Falls back to structlog-only logging if Langfuse is unavailable.
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        enabled: bool = True,
    ) -> None:
        global _langfuse_client, _langfuse_available

        self._public_key = public_key
        self._secret_key = secret_key
        self._host = host or "https://cloud.langfuse.com"
        self._enabled = enabled and bool(public_key) and bool(secret_key)
        self._client: Any = None
        self._traces: dict[str, Any] = {}  # trace_id -> langfuse trace object
        self._spans: dict[str, Any] = {}   # span_id -> langfuse span object

        if self._enabled:
            try:
                from langfuse import Langfuse
                self._client = Langfuse(
                    public_key=self._public_key,
                    secret_key=self._secret_key,
                    host=self._host,
                )
                _langfuse_client = self._client
                _langfuse_available = True
                logger.info("langfuse_tracer_init", host=self._host, connected=True)
            except Exception as exc:
                _langfuse_available = False
                logger.warning("langfuse_tracer_init_failed", error=str(exc), host=self._host)
        else:
            _langfuse_available = False
            logger.info("langfuse_tracer_init", host=self._host, enabled=False)

    @property
    def connected(self) -> bool:
        """Whether a real Langfuse client is active."""
        return self._client is not None

    async def create_trace(self, name: str, metadata: dict[str, Any]) -> str:
        trace_id = str(uuid.uuid4())
        if self._client:
            try:
                trace = self._client.trace(
                    id=trace_id,
                    name=name,
                    metadata=metadata,
                )
                self._traces[trace_id] = trace
                logger.debug("langfuse_trace_created", trace_id=trace_id, name=name)
            except Exception as exc:
                logger.warning("langfuse_trace_create_failed", error=str(exc), trace_id=trace_id)
        else:
            logger.info("langfuse_trace_created", trace_id=trace_id, name=name, fallback=True)
        return trace_id

    async def create_span(self, trace_id: str, name: str, metadata: dict[str, Any] | None = None) -> str:
        span_id = str(uuid.uuid4())
        trace_obj = self._traces.get(trace_id)
        if trace_obj and self._client:
            try:
                span = trace_obj.span(
                    id=span_id,
                    name=name,
                    metadata=metadata or {},
                )
                self._spans[span_id] = span
                logger.debug("langfuse_span_created", trace_id=trace_id, span_id=span_id, name=name)
            except Exception as exc:
                logger.warning("langfuse_span_create_failed", error=str(exc), span_id=span_id)
        else:
            logger.info("langfuse_span_created", trace_id=trace_id, span_id=span_id, name=name, fallback=True)
        return span_id

    async def finish_span(self, trace_id: str, span_id: str, metadata: dict[str, Any] | None = None) -> None:
        span_obj = self._spans.pop(span_id, None)
        if span_obj:
            try:
                span_obj.end(metadata=metadata or {})
                logger.debug("langfuse_span_finished", trace_id=trace_id, span_id=span_id)
            except Exception as exc:
                logger.warning("langfuse_span_finish_failed", error=str(exc), span_id=span_id)
        else:
            logger.info("langfuse_span_finished", trace_id=trace_id, span_id=span_id, fallback=True)

    async def finish_trace(self, trace_id: str, metadata: dict[str, Any] | None = None) -> None:
        trace_obj = self._traces.pop(trace_id, None)
        if trace_obj:
            try:
                if metadata:
                    trace_obj.update(metadata=metadata)
                logger.debug("langfuse_trace_finished", trace_id=trace_id)
            except Exception as exc:
                logger.warning("langfuse_trace_finish_failed", error=str(exc), trace_id=trace_id)
        else:
            logger.info("langfuse_trace_finished", trace_id=trace_id, fallback=True)
        # Flush to ensure data is sent
        if self._client:
            try:
                self._client.flush()
            except Exception:
                pass

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        # Langfuse traces are sent to cloud; local lookup not supported
        logger.debug("langfuse_get_trace", trace_id=trace_id, note="remote only")
        return None

    def score(self, *, trace_id: str, name: str, value: float, comment: str | None = None) -> None:
        """Record a Langfuse score (e.g. rubric evaluation result)."""
        if self._client:
            try:
                self._client.score(
                    trace_id=trace_id,
                    name=name,
                    value=value,
                    comment=comment,
                )
                logger.info("langfuse_score_recorded", trace_id=trace_id, name=name, value=value)
            except Exception as exc:
                logger.warning("langfuse_score_failed", error=str(exc), trace_id=trace_id)
        else:
            logger.info("langfuse_score_recorded", trace_id=trace_id, name=name, value=value, fallback=True)

    def generation(
        self,
        *,
        trace_id: str,
        name: str,
        model: str,
        input_data: Any = None,
        output_data: Any = None,
        usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an LLM generation event within a trace."""
        trace_obj = self._traces.get(trace_id)
        if trace_obj and self._client:
            try:
                trace_obj.generation(
                    name=name,
                    model=model,
                    input=input_data,
                    output=output_data,
                    usage=usage or {},
                    metadata=metadata or {},
                )
                logger.debug("langfuse_generation_recorded", trace_id=trace_id, name=name, model=model)
            except Exception as exc:
                logger.warning("langfuse_generation_failed", error=str(exc), trace_id=trace_id)
        else:
            logger.info(
                "langfuse_generation_recorded",
                trace_id=trace_id, name=name, model=model, fallback=True,
            )

    async def check_health(self) -> dict[str, Any]:
        """Check Langfuse connectivity. Returns status dict."""
        if not self._enabled:
            return {"status": "disabled", "message": "Langfuse not enabled (missing keys or enabled=false)"}
        if not self._client:
            return {"status": "error", "message": "Langfuse client failed to initialize"}
        try:
            auth_ok = self._client.auth_check()
            if auth_ok:
                return {"status": "ok", "message": f"Langfuse connected ({self._host})"}
            return {"status": "error", "message": "Langfuse auth check failed"}
        except Exception as exc:
            return {"status": "error", "message": f"Langfuse check failed: {exc}"}

    def shutdown(self) -> None:
        """Flush and shutdown the Langfuse client."""
        if self._client:
            try:
                self._client.flush()
                self._client.shutdown()
                logger.info("langfuse_shutdown")
            except Exception as exc:
                logger.warning("langfuse_shutdown_failed", error=str(exc))


# ---------------------------------------------------------------------------
# trace_llm_call decorator
# ---------------------------------------------------------------------------

def trace_llm_call(
    name: str | None = None,
    *,
    capture_input: bool = True,
    capture_output: bool = True,
) -> Callable:
    """Decorator that traces async function calls in Langfuse.

    Usage:
        @trace_llm_call(name="classifier.classify")
        async def classify(self, text: str, ...) -> dict:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        trace_name = name or f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = get_langfuse_client()
            if not client:
                return await fn(*args, **kwargs)

            trace_id = str(uuid.uuid4())
            start_ts = time.monotonic()

            try:
                trace = client.trace(
                    id=trace_id,
                    name=trace_name,
                    input=_safe_serialize(args, kwargs) if capture_input else None,
                )
            except Exception:
                return await fn(*args, **kwargs)

            try:
                result = await fn(*args, **kwargs)
                duration_ms = (time.monotonic() - start_ts) * 1000

                try:
                    trace.update(
                        output=_safe_serialize_output(result) if capture_output else None,
                        metadata={"duration_ms": round(duration_ms, 1)},
                    )
                    client.flush()
                except Exception as exc:
                    logger.debug("trace_llm_call_update_failed", error=str(exc))

                return result

            except Exception as exc:
                try:
                    trace.update(
                        metadata={"error": str(exc), "error_type": type(exc).__name__},
                    )
                    client.flush()
                except Exception:
                    pass
                raise

        return wrapper
    return decorator


def _safe_serialize(args: tuple, kwargs: dict) -> dict[str, Any]:
    """Best-effort serialize function arguments for Langfuse."""
    try:
        # Skip 'self' argument
        clean_args = args[1:] if args and hasattr(args[0], "__class__") else args
        return {
            "args": [str(a)[:500] for a in clean_args],
            "kwargs": {k: str(v)[:500] for k, v in kwargs.items()},
        }
    except Exception:
        return {"note": "args not serializable"}


def _safe_serialize_output(result: Any) -> Any:
    """Best-effort serialize function output for Langfuse."""
    try:
        if isinstance(result, dict):
            return {k: str(v)[:1000] for k, v in result.items()}
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return str(result)[:2000]
    except Exception:
        return {"note": "output not serializable"}


# ---------------------------------------------------------------------------
# High-level manager
# ---------------------------------------------------------------------------

class TraceManager:
    """High-level tracing API that delegates to a pluggable backend."""

    def __init__(self, backend: TracerBackend) -> None:
        self._backend = backend

    @property
    def backend(self) -> TracerBackend:
        """Access the underlying tracer backend."""
        return self._backend

    async def start_trace(self, name: str, metadata: dict[str, Any] | None = None) -> str:
        """Start a new trace and return its ID."""
        return await self._backend.create_trace(name, metadata or {})

    async def start_span(self, trace_id: str, name: str, metadata: dict[str, Any] | None = None) -> str:
        """Start a span within an existing trace and return its ID."""
        return await self._backend.create_span(trace_id, name, metadata)

    async def end_span(self, trace_id: str, span_id: str, metadata: dict[str, Any] | None = None) -> None:
        """End a span."""
        await self._backend.finish_span(trace_id, span_id, metadata)

    async def end_trace(self, trace_id: str, metadata: dict[str, Any] | None = None) -> None:
        """End a trace."""
        await self._backend.finish_trace(trace_id, metadata)

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Retrieve a trace."""
        return await self._backend.get_trace(trace_id)
