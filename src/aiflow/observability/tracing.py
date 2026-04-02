"""Tracing abstraction - pluggable trace/span management.

Provides:
    - TraceManager: high-level API to start/end traces and spans
    - InMemoryTracer: in-memory implementation for testing
    - LangfuseTracer: placeholder for Langfuse integration

Usage:
    from aiflow.observability.tracing import TraceManager, InMemoryTracer
    backend = InMemoryTracer()
    manager = TraceManager(backend)
    trace_id = await manager.start_trace("my-workflow", {"user": "abc"})
    span_id = await manager.start_span(trace_id, "step-1")
    await manager.end_span(trace_id, span_id)
    await manager.end_trace(trace_id)
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "SpanRecord",
    "TraceRecord",
    "TracerBackend",
    "InMemoryTracer",
    "LangfuseTracer",
    "TraceManager",
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
# Langfuse placeholder
# ---------------------------------------------------------------------------

class LangfuseTracer(TracerBackend):
    """Langfuse-backed tracer (requires ``langfuse`` SDK).

    This is a placeholder implementation. Wire up real Langfuse calls
    once the SDK is installed and configured.
    """

    def __init__(self, public_key: str | None = None, secret_key: str | None = None, host: str | None = None) -> None:
        self._public_key = public_key
        self._secret_key = secret_key
        self._host = host or "http://localhost:3000"
        # Stub: wire langfuse.Langfuse(public_key, secret_key, host) when SDK is installed
        logger.info("langfuse_tracer_init", host=self._host, stub=True)

    async def create_trace(self, name: str, metadata: dict[str, Any]) -> str:
        trace_id = str(uuid.uuid4())
        logger.info("langfuse_trace_created", trace_id=trace_id, name=name, stub=True)
        return trace_id

    async def create_span(self, trace_id: str, name: str, metadata: dict[str, Any] | None = None) -> str:
        span_id = str(uuid.uuid4())
        logger.info("langfuse_span_created", trace_id=trace_id, span_id=span_id, name=name, stub=True)
        return span_id

    async def finish_span(self, trace_id: str, span_id: str, metadata: dict[str, Any] | None = None) -> None:
        logger.info("langfuse_span_finished", trace_id=trace_id, span_id=span_id, stub=True)

    async def finish_trace(self, trace_id: str, metadata: dict[str, Any] | None = None) -> None:
        logger.info("langfuse_trace_finished", trace_id=trace_id, stub=True)

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        logger.info("langfuse_get_trace", trace_id=trace_id, stub=True)
        return None


# ---------------------------------------------------------------------------
# High-level manager
# ---------------------------------------------------------------------------

class TraceManager:
    """High-level tracing API that delegates to a pluggable backend."""

    def __init__(self, backend: TracerBackend) -> None:
        self._backend = backend

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
