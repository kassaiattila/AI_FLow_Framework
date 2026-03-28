"""
@test_registry:
    suite: core-unit
    component: observability.metrics
    covers: [src/aiflow/observability/metrics.py]
    phase: 6
    priority: medium
    estimated_duration_ms: 300
    requires_services: []
    tags: [observability, metrics, counter, histogram, gauge]
"""
import pytest

from aiflow.observability.metrics import MetricsCollector, InMemoryMetrics


class TestInMemoryMetrics:
    """Verify InMemoryMetrics stores counters, histograms, and gauges."""

    @pytest.fixture
    def metrics(self):
        return InMemoryMetrics()

    def test_counter_increment(self, metrics):
        metrics.increment_counter("requests_total")
        assert metrics.get_counter("requests_total") == 1.0

    def test_counter_increment_multiple(self, metrics):
        metrics.increment_counter("requests_total", amount=1.0)
        metrics.increment_counter("requests_total", amount=3.0)
        assert metrics.get_counter("requests_total") == 4.0

    def test_histogram_observe(self, metrics):
        metrics.observe_histogram("latency_ms", value=150.0)
        metrics.observe_histogram("latency_ms", value=250.0)
        observations = metrics.get_histogram("latency_ms")
        assert len(observations) == 2
        assert 150.0 in observations
        assert 250.0 in observations

    def test_gauge_set(self, metrics):
        metrics.set_gauge("active_workflows", value=5.0)
        assert metrics.get_gauge("active_workflows") == 5.0

    def test_gauge_overwrite(self, metrics):
        metrics.set_gauge("active_workflows", value=5.0)
        metrics.set_gauge("active_workflows", value=3.0)
        assert metrics.get_gauge("active_workflows") == 3.0

    def test_counter_with_labels(self, metrics):
        metrics.increment_counter("requests_total", labels={"method": "GET"}, amount=1.0)
        metrics.increment_counter("requests_total", labels={"method": "POST"}, amount=2.0)
        metrics.increment_counter("requests_total", labels={"method": "GET"}, amount=1.0)

        assert metrics.get_counter("requests_total", labels={"method": "GET"}) == 2.0
        assert metrics.get_counter("requests_total", labels={"method": "POST"}) == 2.0

    def test_counter_unknown_returns_zero(self, metrics):
        assert metrics.get_counter("nonexistent") == 0.0

    def test_gauge_unknown_returns_zero(self, metrics):
        assert metrics.get_gauge("nonexistent") == 0.0

    def test_histogram_unknown_returns_empty(self, metrics):
        assert metrics.get_histogram("nonexistent") == []


class TestMetricsCollectorIsAbstract:
    """Verify MetricsCollector is an abstract base class."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            MetricsCollector()

    def test_in_memory_is_subclass(self):
        assert issubclass(InMemoryMetrics, MetricsCollector)

    def test_in_memory_delegates_correctly(self):
        backend = InMemoryMetrics()
        backend.increment_counter("test_counter", amount=1.0)
        assert backend.get_counter("test_counter") == 1.0
