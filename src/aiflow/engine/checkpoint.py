"""Checkpoint management for workflow resume after failure.

Inspired by LangGraph checkpoint system with version tracking.
Each checkpoint captures the state after a successful step completion.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["Checkpoint", "CheckpointManager"]

logger = structlog.get_logger(__name__)


class Checkpoint(BaseModel):
    """A snapshot of workflow state at a specific point."""

    workflow_run_id: str
    step_name: str
    step_index: int
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # State data
    completed_steps: list[str] = []
    step_outputs: dict[str, Any] = {}
    accumulated_cost_usd: float = 0.0
    metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize checkpoint for storage in JSONB."""
        return {
            "workflow_run_id": self.workflow_run_id,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "completed_steps": self.completed_steps,
            "step_outputs": self.step_outputs,
            "accumulated_cost_usd": self.accumulated_cost_usd,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Deserialize checkpoint from JSONB storage."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class CheckpointManager:
    """Manages checkpoint creation and retrieval during workflow execution.

    In Phase 1, checkpoints are stored in step_runs.checkpoint_data (JSONB).
    In production, this could be backed by Redis for faster access.
    """

    def __init__(self) -> None:
        self._checkpoints: dict[str, list[Checkpoint]] = {}  # run_id -> checkpoints

    def save(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint after successful step completion."""
        run_id = checkpoint.workflow_run_id
        if run_id not in self._checkpoints:
            self._checkpoints[run_id] = []
        self._checkpoints[run_id].append(checkpoint)
        logger.info(
            "checkpoint_saved",
            run_id=run_id,
            step=checkpoint.step_name,
            version=checkpoint.version,
            completed=len(checkpoint.completed_steps),
        )

    def get_latest(self, workflow_run_id: str) -> Checkpoint | None:
        """Get the most recent checkpoint for a workflow run."""
        checkpoints = self._checkpoints.get(workflow_run_id, [])
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda c: c.version)

    def get_by_step(self, workflow_run_id: str, step_name: str) -> Checkpoint | None:
        """Get checkpoint for a specific step."""
        checkpoints = self._checkpoints.get(workflow_run_id, [])
        for cp in reversed(checkpoints):
            if cp.step_name == step_name:
                return cp
        return None

    def get_all(self, workflow_run_id: str) -> list[Checkpoint]:
        """Get all checkpoints for a workflow run, ordered by version."""
        checkpoints = self._checkpoints.get(workflow_run_id, [])
        return sorted(checkpoints, key=lambda c: c.version)

    def clear(self, workflow_run_id: str) -> None:
        """Clear all checkpoints for a workflow run (after completion)."""
        self._checkpoints.pop(workflow_run_id, None)

    def clear_all(self) -> None:
        """Clear all checkpoints (for testing)."""
        self._checkpoints.clear()
