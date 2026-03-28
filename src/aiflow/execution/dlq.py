"""Dead Letter Queue for failed jobs that exceeded retry limits."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["DLQEntry", "DeadLetterQueue"]

logger = structlog.get_logger(__name__)


class DLQEntry(BaseModel):
    """An entry in the dead letter queue."""

    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    workflow_name: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    error: str
    retry_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeadLetterQueue:
    """In-memory dead letter queue for failed jobs."""

    def __init__(self) -> None:
        self._entries: dict[str, DLQEntry] = {}

    async def add(self, entry: DLQEntry) -> str:
        """Add a failed job to the DLQ. Returns entry_id."""
        self._entries[entry.entry_id] = entry
        logger.warning("dlq_entry_added", entry_id=entry.entry_id, job_id=entry.job_id)
        return entry.entry_id

    async def list_entries(self, limit: int = 100) -> list[DLQEntry]:
        """List DLQ entries, most recent first."""
        entries = sorted(
            self._entries.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )
        return entries[:limit]

    async def get(self, entry_id: str) -> DLQEntry | None:
        """Get a specific DLQ entry."""
        return self._entries.get(entry_id)

    async def remove(self, entry_id: str) -> bool:
        """Remove an entry from the DLQ. Returns True if removed."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            logger.info("dlq_entry_removed", entry_id=entry_id)
            return True
        return False

    async def replay(self, entry_id: str) -> DLQEntry | None:
        """Mark entry for replay by removing it from DLQ.

        Returns the entry if found, None otherwise.
        The caller is responsible for re-enqueuing.
        """
        entry = self._entries.pop(entry_id, None)
        if entry:
            logger.info("dlq_entry_replayed", entry_id=entry_id, job_id=entry.job_id)
        return entry

    async def count(self) -> int:
        """Return the number of entries in the DLQ."""
        return len(self._entries)
