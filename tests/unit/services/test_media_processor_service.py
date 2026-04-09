"""
@test_registry:
    suite: service-unit
    component: services.media_processor
    covers: [src/aiflow/services/media_processor/service.py]
    phase: B2.1
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, media-processor, postgresql, stt]
"""

from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from aiflow.services.media_processor.service import (
    MediaJobRecord,
    MediaProcessorConfig,
    MediaProcessorService,
)


def _make_job_row(
    status: str = "completed",
    filename: str = "test.mp4",
) -> dict:
    now = datetime.now(UTC)
    return {
        "id": "job-001",
        "filename": filename,
        "media_type": "video",
        "file_size_bytes": 1024000,
        "duration_seconds": 120.5,
        "stt_provider": "whisper",
        "status": status,
        "transcript_raw": "Hello world transcript",
        "transcript_structured": json.dumps({"title": "Test", "sections": []}),
        "metadata": "{}",
        "error": None,
        "processing_time_ms": 5000.0,
        "created_by": "admin",
        "created_at": now,
        "updated_at": now,
    }


async def _mock_step(data):
    return {**data, "full_text": "transcript text", "duration_seconds": 10.0}


@pytest.fixture()
def _mock_transcript_pipeline():
    """Inject a mock skills.cubix_course_capture.workflows.transcript_pipeline module."""
    mod = types.ModuleType("skills.cubix_course_capture.workflows.transcript_pipeline")
    mod.probe_audio = _mock_step
    mod.extract_audio = _mock_step
    mod.chunk_audio = _mock_step
    mod.transcribe = _mock_step
    mod.merge_transcripts = _mock_step
    mod.structure_transcript = _mock_step

    # Also register parent packages so `from skills.X.Y import Z` works
    for pkg in [
        "skills",
        "skills.cubix_course_capture",
        "skills.cubix_course_capture.workflows",
    ]:
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)

    old = sys.modules.get("skills.cubix_course_capture.workflows.transcript_pipeline")
    sys.modules["skills.cubix_course_capture.workflows.transcript_pipeline"] = mod
    yield mod
    if old is not None:
        sys.modules["skills.cubix_course_capture.workflows.transcript_pipeline"] = old
    else:
        sys.modules.pop("skills.cubix_course_capture.workflows.transcript_pipeline", None)


@pytest.fixture()
def svc(mock_pool) -> MediaProcessorService:
    pool, _conn = mock_pool
    service = MediaProcessorService(config=MediaProcessorConfig())
    service._pool = pool
    return service


class TestMediaProcessorService:
    @pytest.mark.asyncio
    async def test_process_media_creates_job(
        self,
        svc: MediaProcessorService,
        mock_pool,
        tmp_path,
        _mock_transcript_pipeline,
    ) -> None:
        """process_media creates a job record and processes file."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="INSERT 0 1")

        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"\x00" * 1024)

        record = await svc.process_media(test_file)

        assert isinstance(record, MediaJobRecord)
        assert record.status == "completed"
        assert record.filename == "test.mp4"

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, svc: MediaProcessorService, mock_pool) -> None:
        """list_jobs returns paginated results with total count."""
        _pool, conn = mock_pool
        conn.fetchval = AsyncMock(return_value=2)
        conn.fetch = AsyncMock(return_value=[_make_job_row(), _make_job_row(filename="test2.mp4")])

        jobs, total = await svc.list_jobs(limit=10, offset=0)
        assert total == 2
        assert len(jobs) == 2
        assert all(isinstance(j, MediaJobRecord) for j in jobs)

    @pytest.mark.asyncio
    async def test_get_job_existing(self, svc: MediaProcessorService, mock_pool) -> None:
        """get_job returns MediaJobRecord for existing ID."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=_make_job_row())

        job = await svc.get_job("job-001")
        assert job is not None
        assert job.id == "job-001"
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, svc: MediaProcessorService, mock_pool) -> None:
        """get_job returns None for non-existent ID."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=None)

        job = await svc.get_job("nonexistent")
        assert job is None

    @pytest.mark.asyncio
    async def test_delete_job(self, svc: MediaProcessorService, mock_pool) -> None:
        """delete_job returns True when row is deleted."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="DELETE 1")

        result = await svc.delete_job("job-001")
        assert result is True
