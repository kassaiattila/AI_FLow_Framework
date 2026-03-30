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
    SkillInfoItem(
        name="qbpp_test_automation",
        display_name="QBPP Test Automation",
        status="stub",
        skill_type="rpa",
        description="Insurance calculator test automation",
    ),
]


@router.get("", response_model=SkillListResponse)
async def list_skills() -> SkillListResponse:
    """List all installed skills."""
    return SkillListResponse(skills=_SKILLS, total=len(_SKILLS))
