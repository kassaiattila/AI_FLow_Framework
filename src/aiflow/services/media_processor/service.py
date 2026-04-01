"""Media Processor service implementation.

Processes video/audio files through STT pipeline (Whisper/Azure Speech),
persists results to media_jobs table.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["MediaProcessorConfig", "MediaProcessorService"]

logger = structlog.get_logger(__name__)


class MediaProcessorConfig(BaseModel):
    """Configuration for Media Processor service."""
    default_stt_provider: str = Field(default="whisper")
    max_file_size_mb: int = Field(default=500)
    supported_formats: list[str] = Field(default=["mp4", "mkv", "mp3", "wav", "m4a", "webm", "ogg"])


class MediaJobRecord(BaseModel):
    """A persisted media processing job."""
    id: str
    filename: str
    media_type: str = "video"
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    stt_provider: str = "whisper"
    status: str = "pending"
    transcript_raw: str | None = None
    transcript_structured: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    processing_time_ms: float | None = None
    created_by: str | None = None
    created_at: str = ""
    updated_at: str = ""


class MediaProcessorService:
    """Service for processing media files through STT pipeline."""

    def __init__(self, config: MediaProcessorConfig | None = None, db_url: str | None = None):
        self.config = config or MediaProcessorConfig()
        self._db_url = db_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            url = self._db_url or os.getenv(
                "AIFLOW_DATABASE__URL",
                "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
            ).replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
        return self._pool

    async def process_media(
        self, file_path: Path, stt_provider: str | None = None, created_by: str | None = None,
    ) -> MediaJobRecord:
        """Process a media file: probe → extract audio → chunk → STT → merge → structure."""
        job_id = str(uuid.uuid4())
        provider = stt_provider or self.config.default_stt_provider
        filename = file_path.name
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Create job record in DB
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO media_jobs (id, filename, media_type, file_size_bytes, stt_provider, status, created_by, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, 'running', $6, $7, $7)""",
                job_id, filename, _detect_media_type(filename), file_size, provider,
                created_by, datetime.now(timezone.utc),
            )

        start = time.time()
        try:
            from skills.cubix_course_capture.workflows.transcript_pipeline import (
                probe_audio, extract_audio, chunk_audio, transcribe,
                merge_transcripts, structure_transcript,
            )

            data: dict[str, Any] = {"file_path": str(file_path), "output_dir": str(file_path.parent)}
            data = await probe_audio(data)
            duration = data.get("duration_seconds")
            data = await extract_audio(data)
            data = await chunk_audio(data)
            data = await transcribe(data)
            data = await merge_transcripts(data)
            data = await structure_transcript(data)

            elapsed = (time.time() - start) * 1000
            transcript_raw = data.get("merged_text", "")
            transcript_structured = data.get("structured_transcript")

            # Update job record
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE media_jobs SET status='completed', transcript_raw=$2,
                       transcript_structured=$3::jsonb, duration_seconds=$4,
                       processing_time_ms=$5, updated_at=$6
                       WHERE id=$1""",
                    job_id, transcript_raw, _to_json(transcript_structured),
                    duration, elapsed, datetime.now(timezone.utc),
                )

            logger.info("media_processed", job_id=job_id, duration_s=duration, elapsed_ms=elapsed)
            return MediaJobRecord(
                id=job_id, filename=filename, media_type=_detect_media_type(filename),
                file_size_bytes=file_size, duration_seconds=duration,
                stt_provider=provider, status="completed",
                transcript_raw=transcript_raw, transcript_structured=transcript_structured,
                processing_time_ms=elapsed, created_by=created_by,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            error_msg = str(e)
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE media_jobs SET status='failed', error=$2, processing_time_ms=$3, updated_at=$4 WHERE id=$1",
                    job_id, error_msg, elapsed, datetime.now(timezone.utc),
                )
            logger.error("media_processing_failed", job_id=job_id, error=error_msg)
            return MediaJobRecord(
                id=job_id, filename=filename, status="failed",
                error=error_msg, processing_time_ms=elapsed,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> tuple[list[MediaJobRecord], int]:
        """List media processing jobs with pagination."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM media_jobs")
            rows = await conn.fetch(
                "SELECT * FROM media_jobs ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
        return [_row_to_record(r) for r in rows], total

    async def get_job(self, job_id: str) -> MediaJobRecord | None:
        """Get a single job by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM media_jobs WHERE id = $1", job_id)
        return _row_to_record(row) if row else None

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM media_jobs WHERE id = $1", job_id)
        return result == "DELETE 1"


def _detect_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
        return "audio"
    return "video"


def _to_json(data: Any) -> str | None:
    if data is None:
        return None
    import json
    return json.dumps(data)


def _row_to_record(row) -> MediaJobRecord:
    import json
    return MediaJobRecord(
        id=row["id"],
        filename=row["filename"],
        media_type=row.get("media_type", "video"),
        file_size_bytes=row.get("file_size_bytes"),
        duration_seconds=row.get("duration_seconds"),
        stt_provider=row.get("stt_provider", "whisper"),
        status=row["status"],
        transcript_raw=row.get("transcript_raw"),
        transcript_structured=json.loads(row["transcript_structured"]) if row.get("transcript_structured") else None,
        metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
        error=row.get("error"),
        processing_time_ms=row.get("processing_time_ms"),
        created_by=row.get("created_by"),
        created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
    )
