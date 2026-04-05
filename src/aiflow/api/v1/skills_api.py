"""Skill listing endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


class SkillInfoItem(BaseModel):
    """Skill metadata."""

    name: str
    display_name: str
    status: str
    skill_type: str
    description: str


class SkillListResponse(BaseModel):
    """List of installed skills."""

    skills: list[SkillInfoItem]
    total: int


# Hardcoded skill registry — matches the frontend SKILLS constant
_SKILLS: list[SkillInfoItem] = [
    SkillInfoItem(
        name="process_documentation",
        display_name="Process Documentation",
        status="production",
        skill_type="ai",
        description="Natural language -> BPMN diagrams (Mermaid + DrawIO + SVG)",
    ),
    SkillInfoItem(
        name="cubix_course_capture",
        display_name="Cubix Course Capture",
        status="production",
        skill_type="hybrid",
        description="Video transcript pipeline (ffmpeg + Whisper STT + LLM)",
    ),
    SkillInfoItem(
        name="aszf_rag_chat",
        display_name="ASZF RAG Chat",
        status="production",
        skill_type="ai",
        description="Legal document RAG chat (docling + pgvector + OpenAI)",
    ),
    SkillInfoItem(
        name="email_intent_processor",
        display_name="Email Intent Processor",
        status="in_development",
        skill_type="ai",
        description="Email classification & entity extraction (hybrid ML+LLM)",
    ),
    SkillInfoItem(
        name="invoice_processor",
        display_name="Invoice Processor",
        status="in_development",
        skill_type="ai",
        description="PDF invoice data extraction (Docling + GPT-4o)",
    ),
]


class SkillSummaryItem(BaseModel):
    """Skill with run statistics for dashboard."""

    name: str
    display_name: str
    status: str
    skill_type: str
    description: str
    run_count: int = 0
    last_run_at: str | None = None
    success_rate: float = 0.0


class SkillSummaryResponse(BaseModel):
    """Skills with run stats for dashboard cards."""

    skills: list[SkillSummaryItem]
    total: int
    source: str = "backend"


@router.get("", response_model=SkillListResponse)
async def list_skills() -> SkillListResponse:
    """List all installed skills."""
    return SkillListResponse(skills=_SKILLS, total=len(_SKILLS))


@router.get("/summary", response_model=SkillSummaryResponse)
async def get_skills_summary() -> SkillSummaryResponse:
    """Get skills with run statistics for dashboard skill cards."""
    from aiflow.api.deps import get_pool

    # Start with static skill data
    skill_stats: dict[str, dict] = {}

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    skill_name,
                    COUNT(*) AS run_count,
                    MAX(started_at) AS last_run_at,
                    ROUND(
                        COUNT(*) FILTER (WHERE status = 'completed')::numeric
                        / NULLIF(COUNT(*), 0) * 100, 1
                    ) AS success_rate
                FROM workflow_runs
                WHERE skill_name IS NOT NULL
                GROUP BY skill_name
                """
            )
            for row in rows:
                skill_stats[row["skill_name"]] = {
                    "run_count": row["run_count"],
                    "last_run_at": row["last_run_at"].isoformat() if row["last_run_at"] else None,
                    "success_rate": float(row["success_rate"] or 0),
                }
    except Exception as e:
        logger.warning("skill_summary_db_failed", error=str(e))

    items = []
    for s in _SKILLS:
        stats = skill_stats.get(s.name, {})
        items.append(
            SkillSummaryItem(
                name=s.name,
                display_name=s.display_name,
                status=s.status,
                skill_type=s.skill_type,
                description=s.description,
                run_count=stats.get("run_count", 0),
                last_run_at=stats.get("last_run_at"),
                success_rate=stats.get("success_rate", 0.0),
            )
        )

    return SkillSummaryResponse(skills=items, total=len(items))
