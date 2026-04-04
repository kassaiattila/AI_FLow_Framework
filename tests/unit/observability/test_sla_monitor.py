"""
@test_registry:
    suite: core-unit
    component: observability.sla_monitor
    covers: [src/aiflow/observability/sla_monitor.py]
    phase: 6
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [observability, sla, latency, success_rate]
"""
import pytest

from aiflow.observability.sla_monitor import SLADefinition, SLAMonitor, SLAResult


class TestSLADefinition:
    """Verify SLADefinition data model."""

    def test_create_sla_definition(self):
        sla = SLADefinition(
            workflow_name="invoice-processing",
            max_duration_seconds=30.0,
            target_success_rate=0.95,
        )
        assert sla.workflow_name == "invoice-processing"
        assert sla.target_success_rate == 0.95
        assert sla.max_duration_seconds == 30.0

    def test_sla_definition_defaults(self):
        sla = SLADefinition(
            workflow_name="default-sla",
            max_duration_seconds=60.0,
        )
        assert sla.workflow_name == "default-sla"
        assert sla.target_success_rate == 0.99  # default
        assert sla.alert_channels == []


class TestSLAMonitor:
    """Verify SLAMonitor tracks runs and evaluates SLA compliance."""

    @pytest.fixture
    def monitor(self):
        return SLAMonitor()

    @pytest.fixture
    def sla(self):
        return SLADefinition(
            workflow_name="test-workflow",
            max_duration_seconds=1.0,  # 1 second = 1000ms
            target_success_rate=0.90,
        )

    @pytest.mark.asyncio
    async def test_record_run(self, monitor):
        await monitor.record_run(
            workflow_name="test-workflow",
            duration_ms=200.0,
            success=True,
        )
        # Runs are recorded internally
        assert len(monitor.runs.get("test-workflow", [])) == 1

    @pytest.mark.asyncio
    async def test_check_sla_met(self, monitor, sla):
        """All runs succeed and are fast -> SLA is met."""
        monitor.register_sla(sla)
        for _ in range(20):
            await monitor.record_run(
                workflow_name="test-workflow",
                duration_ms=300.0,
                success=True,
            )

        result = await monitor.check_sla("test-workflow")
        assert isinstance(result, SLAResult)
        assert result.sla_met is True
        assert result.success_rate == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_check_sla_not_met_success_rate(self, monitor, sla):
        """Too many failures -> SLA not met."""
        monitor.register_sla(sla)
        # 5 successes, 15 failures = 25% success rate (below 90% target)
        for _ in range(5):
            await monitor.record_run(
                workflow_name="test-workflow",
                duration_ms=100.0,
                success=True,
            )
        for _ in range(15):
            await monitor.record_run(
                workflow_name="test-workflow",
                duration_ms=100.0,
                success=False,
            )

        result = await monitor.check_sla("test-workflow")
        assert result.sla_met is False
        assert result.success_rate == pytest.approx(0.25)

    @pytest.mark.asyncio
    async def test_check_sla_not_met_latency(self, monitor, sla):
        """Success rate OK but p95 latency too high -> SLA not met."""
        monitor.register_sla(sla)
        for i in range(100):
            await monitor.record_run(
                workflow_name="test-workflow",
                duration_ms=500.0 if i < 90 else 5000.0,  # 10% very slow
                success=True,
            )

        result = await monitor.check_sla("test-workflow")
        assert result.sla_met is False
        # p95 should exceed the 1000ms target (max_duration_seconds=1.0)
        assert result.p95_ms > 1000.0

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, monitor, sla):
        """Verify success rate is calculated correctly."""
        monitor.register_sla(sla)
        await monitor.record_run(workflow_name="test-workflow", duration_ms=100.0, success=True)
        await monitor.record_run(workflow_name="test-workflow", duration_ms=100.0, success=True)
        await monitor.record_run(workflow_name="test-workflow", duration_ms=100.0, success=False)
        await monitor.record_run(workflow_name="test-workflow", duration_ms=100.0, success=True)

        result = await monitor.check_sla("test-workflow")
        # 3 out of 4 = 75%
        assert result.success_rate == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_percentile_latency_values(self, monitor, sla):
        """Check that p50, p95, p99 are computed and ordered correctly."""
        monitor.register_sla(sla)
        latencies = list(range(1, 101))  # 1ms to 100ms
        for lat in latencies:
            await monitor.record_run(
                workflow_name="test-workflow",
                duration_ms=float(lat),
                success=True,
            )

        result = await monitor.check_sla("test-workflow")
        assert result.p50_ms > 0
        assert result.p95_ms > 0
        assert result.p99_ms > 0
        # p50 <= p95 <= p99
        assert result.p50_ms <= result.p95_ms
        assert result.p95_ms <= result.p99_ms

    @pytest.mark.asyncio
    async def test_sla_result_workflow_name(self, monitor, sla):
        """SLAResult should expose the workflow_name."""
        monitor.register_sla(sla)
        await monitor.record_run(workflow_name="test-workflow", duration_ms=100.0, success=True)
        result = await monitor.check_sla("test-workflow")
        assert result.workflow_name == "test-workflow"

    @pytest.mark.asyncio
    async def test_check_sla_no_data(self, monitor):
        """No recorded runs -> SLA met by default, zero values."""
        result = await monitor.check_sla("unknown-workflow")
        assert result.sla_met is True
        assert result.total_runs == 0
