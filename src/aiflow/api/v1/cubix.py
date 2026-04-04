"""Cubix course capture results endpoint — filesystem scan."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/cubix", tags=["cubix"])


class CubixCourse(BaseModel):
    """A single cubix course result."""

    course_id: str
    course_name: str = ""
    status: str = ""
    sections: list[dict[str, Any]] = []
    duration_seconds: float = 0
    transcript_files: list[str] = []
    created_at: str | None = None


class CubixListResponse(BaseModel):
    """List of cubix course results."""

    courses: list[CubixCourse]
    total: int
    source: str = "filesystem"


def _output_dir() -> Path:
    return Path(
        os.getenv(
            "AIFLOW_CUBIX_OUTPUT_DIR",
            "./skills/cubix_course_capture/output",
        )
    )


@router.get("", response_model=CubixListResponse)
async def list_cubix_courses() -> CubixListResponse:
    """Scan filesystem for cubix course capture results.

    Looks for pipeline_state.json in each subdirectory of the output dir.
    Falls back to empty list if no output exists.
    """
    output_dir = _output_dir()
    courses: list[CubixCourse] = []

    if output_dir.exists():
        for course_dir in sorted(output_dir.iterdir()):
            if not course_dir.is_dir():
                continue
            state_file = course_dir / "pipeline_state.json"
            if not state_file.exists():
                continue
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                # Extract transcript files
                transcripts = [f.name for f in course_dir.glob("*.txt")] + [
                    f.name for f in course_dir.glob("*.md")
                ]

                courses.append(
                    CubixCourse(
                        course_id=course_dir.name,
                        course_name=state.get("course_name", course_dir.name),
                        status=state.get("status", "unknown"),
                        sections=state.get("sections", []),
                        duration_seconds=state.get("total_duration_seconds", 0),
                        transcript_files=transcripts,
                        created_at=state.get("created_at"),
                    )
                )
            except Exception as e:
                logger.warning("cubix_parse_error", dir=course_dir.name, error=str(e))

    if courses:
        logger.info("cubix_courses_loaded", count=len(courses))
        return CubixListResponse(courses=courses, total=len(courses), source="filesystem")

    logger.info("cubix_no_courses_found")
    return CubixListResponse(courses=[], total=0, source="demo")
