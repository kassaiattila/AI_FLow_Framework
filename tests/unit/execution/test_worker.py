"""
@test_registry:
    suite: execution-unit
    component: execution.worker
    covers: [src/aiflow/execution/worker.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [execution, worker, async]
"""
from unittest.mock import AsyncMock

import pytest

from aiflow.execution.queue import InMemoryJobQueue, JobStatus, WorkflowJob
from aiflow.execution.worker import WorkflowWorker


class TestWorkflowWorker:
    @pytest.fixture
    def queue(self):
        return InMemoryJobQueue()

    @pytest.fixture
    def worker(self, queue):
        return WorkflowWorker(queue=queue, worker_id="test-worker")

    def test_worker_creation(self, worker):
        assert worker.worker_id == "test-worker"
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_start_stop(self, worker):
        await worker.start()
        assert worker.is_running is True
        await worker.stop()
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_process_one_empty_queue(self, worker):
        result = await worker.process_one()
        assert result is None

    @pytest.mark.asyncio
    async def test_process_one_with_executor(self, queue):
        executor = AsyncMock(return_value={"output": "success"})
        worker = WorkflowWorker(queue=queue, executor=executor, worker_id="exec-worker")
        job = WorkflowJob(workflow_name="test-wf")
        await queue.enqueue(job)
        processed = await worker.process_one()
        assert processed is not None
        assert processed.status == JobStatus.COMPLETED
        assert processed.result == {"output": "success"}
        executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_one_executor_failure(self, queue):
        executor = AsyncMock(side_effect=RuntimeError("boom"))
        worker = WorkflowWorker(queue=queue, executor=executor)
        job = WorkflowJob(workflow_name="test-wf")
        await queue.enqueue(job)
        processed = await worker.process_one()
        assert processed is not None
        assert processed.status == JobStatus.FAILED
        assert "boom" in processed.error
