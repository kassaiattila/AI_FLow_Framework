"""Media Processor API endpoints — F4b.

Upload media → STT → transcript + structured output.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from functools import cache
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/media", tags=["media"])


@cache
def _get_service():
    from aiflow.services.media_processor import MediaProcessorService
    return MediaProcessorService()


class MediaJobResponse(BaseModel):
    id: str
    filename: str
    media_type: str = "video"
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    stt_provider: str = "whisper"
    status: str = "pending"
    transcript_raw: str | None = None
    transcript_structured: dict[str, Any] | None = None
    error: str | None = None
    processing_time_ms: float | None = None
    created_at: str = ""
    source: str = "backend"


class MediaJobListResponse(BaseModel):
    jobs: list[MediaJobResponse]
    total: int
    source: str = "backend"


class DeleteResponse(BaseModel):
    deleted: bool = True
    source: str = "backend"


@router.post("/upload", response_model=MediaJobResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    stt_provider: str | None = Query(None),
):
    """Upload a media file and start STT processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    upload_dir = Path(tempfile.mkdtemp(prefix="media_upload_"))
    dest = upload_dir / file.filename
    content = await file.read()
    dest.write_bytes(content)

    svc = _get_service()
    try:
        result = await svc.process_media(dest, stt_provider=stt_provider)
        return MediaJobResponse(**{k: v for k, v in result.model_dump().items() if k in MediaJobResponse.model_fields}, source="backend")
    except Exception as e:
        logger.error("media_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=MediaJobListResponse)
async def list_jobs(limit: int = Query(50), offset: int = Query(0)):
    """List all media processing jobs."""
    svc = _get_service()
    jobs, total = await svc.list_jobs(limit=limit, offset=offset)
    return MediaJobListResponse(
        jobs=[MediaJobResponse(**{k: v for k, v in j.model_dump().items() if k in MediaJobResponse.model_fields}, source="backend") for j in jobs],
        total=total,
    )


@router.get("/{job_id}", response_model=MediaJobResponse)
async def get_job(job_id: str):
    """Get a single media job by ID."""
    svc = _get_service()
    job = await svc.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return MediaJobResponse(**{k: v for k, v in job.model_dump().items() if k in MediaJobResponse.model_fields}, source="backend")


@router.delete("/{job_id}", response_model=DeleteResponse)
async def delete_job(job_id: str):
    """Delete a media job."""
    svc = _get_service()
    deleted = await svc.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return DeleteResponse()
