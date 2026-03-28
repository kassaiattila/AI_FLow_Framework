"""
@test_registry:
    suite: execution-unit
    component: execution.queue
    covers: [src/aiflow/execution/queue.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [execution, queue, priority, async]
"""
import pytest
from datetime import datetime, timezone, timedelta
from aiflow.execution.queue import (
    JobPriority,
    WorkflowJob,
    JobStatus,
    InMemoryJobQueue,
)


class TestWorkflowJob:
    def test_create_with_defaults(self):
        job = WorkflowJob(workflow_name="test-wf")
        assert job.workflow_name == "test-wf"
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.NORMAL
        assert job.input_data == {}
        assert job.result is None
        assert job.error is None
        assert job.job_id is not None

    def test_create_with_all_fields(self):
        job = WorkflowJob(
            workflow_name="test-wf",
            input_data={"key": "value"},
            priority=JobPriority.HIGH,
            team_id="team-1",
            user_id="user-1",
        )
        assert job.input_data == {"key": "value"}
        assert job.priority == JobPriority.HIGH
        assert job.team_id == "team-1"
        assert job.user_id == "user-1"

    def test_job_id_is_unique(self):
        job1 = WorkflowJob(workflow_name="wf-1")
        job2 = WorkflowJob(workflow_name="wf-2")
        assert job1.job_id != job2.job_id


class TestJobPriority:
    def test_critical_is_highest(self):
        assert JobPriority.CRITICAL < JobPriority.HIGH
        assert JobPriority.HIGH < JobPriority.NORMAL
        assert JobPriority.NORMAL < JobPriority.LOW
        assert JobPriority.LOW < JobPriority.BACKGROUND


class TestInMemoryJobQueue:
    @pytest.fixture
    def queue(self):
        return InMemoryJobQueue()

    @pytest.mark.asyncio
    async def test_enqueue_returns_job_id(self, queue):
        job = WorkflowJob(workflow_name="test-wf")
        job_id = await queue.enqueue(job)
        assert job_id == job.job_id

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_on_empty(self, queue):
        result = await queue.dequeue()
        assert result is None

    @pytest.mark.asyncio
    async def test_enqueue_and_dequeue(self, queue):
        job = WorkflowJob(workflow_name="test-wf")
        await queue.enqueue(job)
        dequeued = await queue.dequeue()
        assert dequeued is not None
        assert dequeued.job_id == job.job_id
        assert dequeued.status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_status(self, queue):
        job = WorkflowJob(workflow_name="test-wf")
        await queue.enqueue(job)
        status = await queue.get_status(job.job_id)
        assert status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_status_unknown_job(self, queue):
        status = await queue.get_status("nonexistent-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_result(self, queue):
        job = WorkflowJob(workflow_name="test-wf")
        job.result = {"output": "done"}
        await queue.enqueue(job)
        result = await queue.get_result(job.job_id)
        assert result == {"output": "done"}

    @pytest.mark.asyncio
    async def test_cancel_pending_job(self, queue):
        job = WorkflowJob(workflow_name="test-wf")
        await queue.enqueue(job)
        cancelled = await queue.cancel(job.job_id)
        assert cancelled is True
        status = await queue.get_status(job.job_id)
        assert status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, queue):
        cancelled = await queue.cancel("nonexistent")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue):
        low_job = WorkflowJob(
            workflow_name="low",
            priority=JobPriority.LOW,
            created_at=datetime.now(timezone.utc),
        )
        high_job = WorkflowJob(
            workflow_name="high",
            priority=JobPriority.HIGH,
            created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        )
        await queue.enqueue(low_job)
        await queue.enqueue(high_job)
        first = await queue.dequeue()
        assert first is not None
        assert first.workflow_name == "high"

    @pytest.mark.asyncio
    async def test_size(self, queue):
        assert await queue.size() == 0
        await queue.enqueue(WorkflowJob(workflow_name="wf-1"))
        await queue.enqueue(WorkflowJob(workflow_name="wf-2"))
        assert await queue.size() == 2
