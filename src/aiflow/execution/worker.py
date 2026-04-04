"""Workflow worker that processes jobs from the queue."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from aiflow.execution.queue import JobQueue, JobStatus, WorkflowJob

__all__ = ["WorkflowWorker"]

logger = structlog.get_logger(__name__)


class WorkflowWorker:
    """Processes workflow jobs from a queue."""

    def __init__(
        self,
        queue: JobQueue,
        executor: Callable[[WorkflowJob], Awaitable[Any]] | None = None,
        worker_id: str = "worker-1",
    ) -> None:
        self._queue = queue
        self._executor = executor
        self._worker_id = worker_id
        self._running = False

    @property
    def worker_id(self) -> str:
        """Return worker identifier."""
        return self._worker_id

    @property
    def is_running(self) -> bool:
        """Return whether the worker is running."""
        return self._running

    async def process_one(self) -> WorkflowJob | None:
        """Process a single job from the queue.

        Returns the processed job or None if queue is empty.
        """
        job = await self._queue.dequeue()
        if job is None:
            return None

        logger.info("processing_job", job_id=job.job_id, worker=self._worker_id)

        try:
            if self._executor:
                result = await self._executor(job)
                job.result = result
            job.status = JobStatus.COMPLETED
            logger.info("job_completed", job_id=job.job_id)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            logger.error("job_failed", job_id=job.job_id, error=str(exc))

        return job

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info("worker_started", worker_id=self._worker_id)

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        logger.info("worker_stopped", worker_id=self._worker_id)
