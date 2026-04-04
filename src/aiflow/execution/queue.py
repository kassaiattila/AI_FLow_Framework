"""Async job queue for workflow execution."""

from __future__ import annotations

import asyncio
import itertools
import uuid
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "JobPriority",
    "WorkflowJob",
    "JobStatus",
    "JobQueue",
    "InMemoryJobQueue",
]

logger = structlog.get_logger(__name__)


class JobPriority(IntEnum):
    """Job priority levels (lower = higher priority)."""

    CRITICAL = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30
    BACKGROUND = 40


class JobStatus(str):
    """Job status constants."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowJob(BaseModel):
    """A queued workflow execution job."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    priority: int = JobPriority.NORMAL
    team_id: str | None = None
    user_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = JobStatus.PENDING
    result: Any | None = None
    error: str | None = None


class JobQueue:
    """Abstract job queue interface."""

    async def enqueue(self, job: WorkflowJob) -> str:
        """Enqueue a job. Returns job_id."""
        raise NotImplementedError

    async def dequeue(self) -> WorkflowJob | None:
        """Get next job by priority. Returns None if empty."""
        raise NotImplementedError

    async def get_status(self, job_id: str) -> str | None:
        """Get job status by ID."""
        raise NotImplementedError

    async def get_result(self, job_id: str) -> Any | None:
        """Get job result by ID."""
        raise NotImplementedError

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job. Returns True if cancelled."""
        raise NotImplementedError

    async def size(self) -> int:
        """Return number of pending jobs."""
        raise NotImplementedError


class InMemoryJobQueue(JobQueue):
    """In-memory priority queue for testing and development."""

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, float, int, WorkflowJob]] = (
            asyncio.PriorityQueue()
        )
        self._jobs: dict[str, WorkflowJob] = {}
        self._counter = itertools.count()

    async def enqueue(self, job: WorkflowJob) -> str:
        """Enqueue a job with priority ordering."""
        self._jobs[job.job_id] = job
        # Use (priority, timestamp, seq) for ordering; seq breaks ties
        seq = next(self._counter)
        await self._queue.put((job.priority, job.created_at.timestamp(), seq, job))
        logger.info("job_enqueued", job_id=job.job_id, workflow=job.workflow_name)
        return job.job_id

    async def dequeue(self) -> WorkflowJob | None:
        """Get highest priority job."""
        if self._queue.empty():
            return None
        _, _, _, job = self._queue.get_nowait()
        job.status = JobStatus.RUNNING
        return job

    async def get_status(self, job_id: str) -> str | None:
        """Get job status."""
        job = self._jobs.get(job_id)
        return job.status if job else None

    async def get_result(self, job_id: str) -> Any | None:
        """Get job result."""
        job = self._jobs.get(job_id)
        return job.result if job else None

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            logger.info("job_cancelled", job_id=job_id)
            return True
        return False

    async def size(self) -> int:
        """Return queue size."""
        return self._queue.qsize()
