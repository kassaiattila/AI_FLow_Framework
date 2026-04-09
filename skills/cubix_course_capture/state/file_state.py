"""File-based state manager with atomic JSON persistence."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import structlog
from skills.cubix_course_capture.models import (
    FileProcessingState,
    PipelineState,
    StageStatus,
)

__all__ = ["FileStateManager"]

logger = structlog.get_logger(__name__)


class FileStateManager:
    """Manages pipeline state as a JSON file with atomic writes.

    Features:
    - Atomic saves via write-to-temp + os.replace()
    - Windows file locking retry (antivirus/indexer contention)
    - Resume support: load existing state and continue from last checkpoint
    """

    STATE_FILE = "pipeline_state.json"
    MAX_RETRIES = 5
    RETRY_DELAY = 0.5  # seconds between retries

    def __init__(self, output_dir: str | Path = "./output") -> None:
        self.output_dir = Path(output_dir)
        self._state_path = self.output_dir / "metadata" / self.STATE_FILE

    @property
    def state_path(self) -> Path:
        """Path to the state JSON file."""
        return self._state_path

    def load(self) -> PipelineState:
        """Load state from JSON. Returns empty state if file doesn't exist."""
        if not self._state_path.exists():
            logger.info("state_file_not_found", path=str(self._state_path))
            return PipelineState()

        try:
            raw = self._state_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            state = PipelineState.model_validate(data)
            logger.info(
                "state_loaded",
                path=str(self._state_path),
                total_files=state.total_files,
                completed=state.completed_files,
                failed=state.failed_files,
            )
            return state
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "state_load_failed",
                path=str(self._state_path),
                error=str(exc),
            )
            # Back up corrupt file and return fresh state
            backup = self._state_path.with_suffix(".json.corrupt")
            self._state_path.rename(backup)
            logger.warning("corrupt_state_backed_up", backup=str(backup))
            return PipelineState()

    def save(self, state: PipelineState) -> None:
        """Atomic save: write to temp file, then os.replace().

        Retries up to MAX_RETRIES times on PermissionError,
        which can occur on Windows due to antivirus or file indexer locks.
        """
        state.updated_at = datetime.now(UTC).isoformat()
        self._state_path.parent.mkdir(parents=True, exist_ok=True)

        data = json.dumps(
            state.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )

        last_error: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Write to temp file in the same directory (same filesystem)
                fd, tmp_path = tempfile.mkstemp(
                    dir=str(self._state_path.parent),
                    prefix=".state_",
                    suffix=".tmp",
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(data)
                    # Atomic replace
                    os.replace(tmp_path, str(self._state_path))
                except BaseException:
                    # Clean up temp file on any error
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise

                logger.debug(
                    "state_saved",
                    path=str(self._state_path),
                    total_files=state.total_files,
                    completed=state.completed_files,
                )
                return

            except PermissionError as exc:
                last_error = exc
                logger.warning(
                    "state_save_permission_error",
                    attempt=attempt,
                    max_retries=self.MAX_RETRIES,
                    error=str(exc),
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

        msg = f"Failed to save state after {self.MAX_RETRIES} attempts"
        raise OSError(msg) from last_error

    def init_file(
        self,
        state: PipelineState,
        global_index: int,
        slug: str,
        title: str,
        week_index: int = 0,
        lesson_index: int = 0,
    ) -> FileProcessingState:
        """Initialize a new file entry in state.

        If the slug already exists, returns the existing entry without modification.
        """
        if slug in state.files:
            logger.debug("file_already_in_state", slug=slug)
            return state.files[slug]

        file_state = FileProcessingState(
            global_index=global_index,
            slug=slug,
            title=title,
            week_index=week_index,
            lesson_index=lesson_index,
        )
        state.files[slug] = file_state
        state.total_files = len(state.files)
        logger.info("file_initialized", slug=slug, global_index=global_index)
        return file_state

    def set_stage(
        self,
        state: PipelineState,
        slug: str,
        stage: str,
        status: StageStatus,
        error: str = "",
    ) -> None:
        """Update a stage status for a file.

        Args:
            state: Current pipeline state.
            slug: File identifier.
            stage: Stage name (probe, extract, chunk, transcribe, merge, structure).
            status: New status for the stage.
            error: Error message if status is FAILED.
        """
        if slug not in state.files:
            logger.error("file_not_in_state", slug=slug, stage=stage)
            return

        file_state = state.files[slug]
        valid_stages = ["probe", "extract", "chunk", "transcribe", "merge", "structure"]
        if stage not in valid_stages:
            logger.error("invalid_stage", slug=slug, stage=stage)
            return

        setattr(file_state, stage, status)

        if status == StageStatus.FAILED:
            file_state.last_error = error
            state.failed_files = sum(
                1 for f in state.files.values() if _is_failed(f)
            )
        elif status == StageStatus.COMPLETED and stage == "structure":
            # All stages done
            state.completed_files = sum(
                1 for f in state.files.values() if _is_completed(f)
            )

        logger.info(
            "stage_updated",
            slug=slug,
            stage=stage,
            status=status,
            error=error or None,
        )

    def update_cost(
        self,
        state: PipelineState,
        slug: str,
        stt_cost: float = 0,
        structuring_cost: float = 0,
    ) -> None:
        """Update cost tracking for a file."""
        if slug not in state.files:
            return

        file_state = state.files[slug]
        file_state.stt_cost += stt_cost
        file_state.structuring_cost += structuring_cost
        file_state.total_cost = file_state.stt_cost + file_state.structuring_cost

        state.total_cost_usd = sum(f.total_cost for f in state.files.values())
        logger.debug(
            "cost_updated",
            slug=slug,
            stt_cost=file_state.stt_cost,
            structuring_cost=file_state.structuring_cost,
            total_pipeline_cost=state.total_cost_usd,
        )

    def get_pending(self, state: PipelineState) -> list[FileProcessingState]:
        """Return files that have incomplete stages (not all completed, not all failed)."""
        return [
            f
            for f in state.files.values()
            if not _is_completed(f) and not _is_failed(f)
        ]

    def get_failed(self, state: PipelineState) -> list[FileProcessingState]:
        """Return files that have at least one failed stage."""
        return [f for f in state.files.values() if _is_failed(f)]

    def reset_file(self, state: PipelineState, slug: str) -> None:
        """Reset all stages of a file back to PENDING for retry."""
        if slug not in state.files:
            logger.warning("reset_file_not_found", slug=slug)
            return

        file_state = state.files[slug]
        for stage in ["probe", "extract", "chunk", "transcribe", "merge", "structure"]:
            setattr(file_state, stage, StageStatus.PENDING)
        file_state.last_error = ""

        # Recalculate counters
        state.completed_files = sum(
            1 for f in state.files.values() if _is_completed(f)
        )
        state.failed_files = sum(
            1 for f in state.files.values() if _is_failed(f)
        )
        logger.info("file_reset", slug=slug)


def _is_completed(file_state: FileProcessingState) -> bool:
    """Check if all stages are completed."""
    return all(
        getattr(file_state, stage) == StageStatus.COMPLETED
        for stage in ["probe", "extract", "chunk", "transcribe", "merge", "structure"]
    )


def _is_failed(file_state: FileProcessingState) -> bool:
    """Check if any stage is failed."""
    return any(
        getattr(file_state, stage) == StageStatus.FAILED
        for stage in ["probe", "extract", "chunk", "transcribe", "merge", "structure"]
    )
