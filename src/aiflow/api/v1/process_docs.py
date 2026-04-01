"""Process Documentation generation endpoint.

Runs the process_documentation skill in-process (no subprocess fork).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/process-docs", tags=["process-docs"])


class GenerateRequest(BaseModel):
    """Request to generate process documentation."""
    user_input: str


class GenerateResponse(BaseModel):
    """Generated process documentation result."""
    doc_id: str = ""
    user_input: str = ""
    mermaid_code: str = ""
    review: dict[str, Any] | None = None
    created_at: str = ""
    source: str = "backend"


@router.post("/generate", response_model=GenerateResponse)
async def generate_process_doc(request: GenerateRequest) -> GenerateResponse:
    """Generate BPMN diagram from natural language description.

    Runs the process_documentation skill steps directly in-process.
    """
    if not request.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input is required")

    output_dir = Path(tempfile.mkdtemp(prefix="aiflow_procdoc_"))

    try:
        from skills.process_documentation.workflow import (
            classify_intent,
            elaborate,
            extract,
            review,
            generate_diagram,
            export_all,
        )
    except ImportError as e:
        logger.error("skill_import_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Process documentation skill not available: {e}")

    try:
        input_data = {
            "user_input": request.user_input,
            "output_dir": str(output_dir),
        }
        data = await classify_intent(input_data)
        data = await elaborate(data)
        data = await extract(data)
        data = await review(data)
        data = await generate_diagram(data)
        data = await export_all(data)
    except Exception as e:
        logger.error("generate_process_doc_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # Read generated mermaid code from output
    mermaid_code = data.get("mermaid_code", "")
    if not mermaid_code:
        mmd_file = output_dir / "diagram.mmd"
        if mmd_file.exists():
            mermaid_code = mmd_file.read_text(encoding="utf-8")

    review_data = data.get("review")

    from datetime import datetime
    return GenerateResponse(
        doc_id=data.get("doc_id", f"doc-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        user_input=request.user_input,
        mermaid_code=mermaid_code,
        review=review_data,
        created_at=datetime.now().isoformat(),
        source="backend",
    )
