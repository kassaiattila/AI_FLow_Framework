"""
@test_registry:
    suite: execution-unit
    component: execution.dlq
    covers: [src/aiflow/execution/dlq.py]
    phase: 5
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [execution, dlq, dead-letter-queue]
"""

import pytest

from aiflow.execution.dlq import DeadLetterQueue, DLQEntry


class TestDLQEntry:
    def test_create_entry(self):
        entry = DLQEntry(
            job_id="job-1",
            workflow_name="test-wf",
            error="max retries exceeded",
        )
        assert entry.job_id == "job-1"
        assert entry.workflow_name == "test-wf"
        assert entry.error == "max retries exceeded"
        assert entry.retry_count == 0
        assert entry.entry_id is not None

    def test_entry_with_input_data(self):
        entry = DLQEntry(
            job_id="job-2",
            workflow_name="test-wf",
            input_data={"doc": "test.pdf"},
            error="timeout",
            retry_count=3,
        )
        assert entry.input_data == {"doc": "test.pdf"}
        assert entry.retry_count == 3


class TestDeadLetterQueue:
    @pytest.fixture
    def dlq(self):
        return DeadLetterQueue()

    @pytest.mark.asyncio
    async def test_add_entry(self, dlq):
        entry = DLQEntry(job_id="j1", workflow_name="wf", error="fail")
        entry_id = await dlq.add(entry)
        assert entry_id == entry.entry_id
        assert await dlq.count() == 1

    @pytest.mark.asyncio
    async def test_list_entries(self, dlq):
        for i in range(3):
            await dlq.add(DLQEntry(job_id=f"j{i}", workflow_name="wf", error="fail"))
        entries = await dlq.list_entries()
        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_replay_removes_entry(self, dlq):
        entry = DLQEntry(job_id="j1", workflow_name="wf", error="fail")
        await dlq.add(entry)
        replayed = await dlq.replay(entry.entry_id)
        assert replayed is not None
        assert replayed.job_id == "j1"
        assert await dlq.count() == 0

    @pytest.mark.asyncio
    async def test_replay_nonexistent(self, dlq):
        result = await dlq.replay("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_entry(self, dlq):
        entry = DLQEntry(job_id="j1", workflow_name="wf", error="fail")
        await dlq.add(entry)
        removed = await dlq.remove(entry.entry_id)
        assert removed is True
        assert await dlq.count() == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, dlq):
        removed = await dlq.remove("nonexistent")
        assert removed is False
