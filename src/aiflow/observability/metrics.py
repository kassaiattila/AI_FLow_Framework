"""Prometheus-compatible metrics collection.

Provides an in-memory metrics collector (for testing / local dev) and
a placeholder for real Prometheus integration.

Usage:
    from aiflow.observability.metrics import MetricsCollector, InMemoryMetrics
    metrics = InMemoryMetrics()
    metrics.increment_counter("workflow_runs_total", {"workflow": "summarize", "status": "success"})
    metrics.observe_histogram("workflow_duration_seconds", 1.23, {"workflow": "summarize"})
    metrics.set_gauge("active_workers", 4, {"queue": "default"})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "MetricSample",
    "MetricsCollector",
    "InMemoryMetrics",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class MetricSample(BaseModel):
    """A single metric observation."""

    name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    metric_type: str  # "counter", "histogram", "gauge"


# ---------------------------------------------------------------------------
# Abstract collector
# ---------------------------------------------------------------------------

class MetricsCollector(ABC):
    """Abstract metrics collection interface.

    Implementations should emit counter, histogram, and gauge metrics
    to Prometheus, StatsD, CloudWatch, or any other backend.
    """

    @abstractmethod
    def increment_counter(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        """Increment a counter metric."""

    @abstractmethod
    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record an observation in a histogram metric."""

    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric to a specific value."""

    @abstractmethod
    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Read the current counter value (for testing / inspection)."""

    @abstractmethod
    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Read the current gauge value."""

    @abstractmethod
    def get_histogram(self, name: str, labels: dict[str, str] | None = None) -> list[float]:
        """Read all histogram observations."""


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

def _label_key(labels: dict[str, str] | None) -> str:
    """Create a deterministic hashable key from label dict."""
    if not labels:
        return ""
    return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class InMemoryMetrics(MetricsCollector):
    """In-memory metrics collector for testing and local development.

    Stores counters, gauges, and histogram observations in plain dicts
    so tests can assert on metric values without a Prometheus server.
    """

    def __init__(self) -> None:
        self._counters: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    # -- counters -----------------------------------------------------------

    def increment_counter(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        key = _label_key(labels)
        self._counters[name][key] += amount
        logger.debug("metric_counter_inc", name=name, labels=labels, amount=amount)

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = _label_key(labels)
        return self._counters.get(name, {}).get(key, 0.0)

    # -- histograms ---------------------------------------------------------

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = _label_key(labels)
        self._histograms[name][key].append(value)
        logger.debug("metric_histogram_obs", name=name, labels=labels, value=value)

    def get_histogram(self, name: str, labels: dict[str, str] | None = None) -> list[float]:
        key = _label_key(labels)
        return list(self._histograms.get(name, {}).get(key, []))

    # -- gauges -------------------------------------------------------------

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = _label_key(labels)
        self._gauges[name][key] = value
        logger.debug("metric_gauge_set", name=name, labels=labels, value=value)

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = _label_key(labels)
        return self._gauges.get(name, {}).get(key, 0.0)

    # -- introspection (test helper) ----------------------------------------

    def reset(self) -> None:
        """Clear all stored metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    @property
    def all_counters(self) -> dict[str, dict[str, float]]:
        """Raw counter storage."""
        return dict(self._counters)

    @property
    def all_gauges(self) -> dict[str, dict[str, float]]:
        """Raw gauge storage."""
        return dict(self._gauges)

    @property
    def all_histograms(self) -> dict[str, dict[str, list[float]]]:
        """Raw histogram storage."""
        return dict(self._histograms)
