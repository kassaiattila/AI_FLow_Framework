"""Process Documentation generation endpoint.

Runs the process_documentation skill in-process (no subprocess fork).
"""
from __future__ import annotations

import json
import os
import tempfile
import time as _time
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aiflow.api.deps import get_pool

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

    run_id = str(uuid.uuid4())
    run_start = _time.perf_counter()
    step_records: list[dict[str, Any]] = []
    run_status = "completed"
    run_error: str | None = None

    try:
        input_data = {
            "user_input": request.user_input,
            "output_dir": str(output_dir),
        }
        steps = [
            ("classify_intent", classify_intent),
            ("elaborate", elaborate),
            ("extract", extract),
            ("review", review),
            ("generate_diagram", generate_diagram),
            ("export_all", export_all),
        ]
        data = input_data
        for step_name, step_fn in steps:
            t = _time.perf_counter()
            data = await step_fn(data)
            elapsed_ms = int((_time.perf_counter() - t) * 1000)
            step_records.append({"name": step_name, "status": "completed", "duration_ms": elapsed_ms})
    except Exception as e:
        run_status = "failed"
        run_error = str(e)
        logger.error("generate_process_doc_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        total_duration_ms = int((_time.perf_counter() - run_start) * 1000)
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO workflow_runs
                       (id, workflow_name, workflow_version, skill_name, status, input_data,
                        started_at, completed_at, total_duration_ms, total_cost_usd, error)
                       VALUES ($1, $2, $3, $4, $5, $6,
                               NOW() - MAKE_INTERVAL(secs := $7::float / 1000),
                               NOW(), $7, $8, $9)""",
                    uuid.UUID(run_id), "bpmn_generation", "1.0", "process_documentation",
                    run_status, json.dumps({"user_input": request.user_input[:100]}),
                    float(total_duration_ms), 0.0, run_error,
                )
                for idx, sr in enumerate(step_records):
                    await conn.execute(
                        """INSERT INTO step_runs
                           (id, workflow_run_id, step_name, step_index, status, duration_ms)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        uuid.uuid4(), uuid.UUID(run_id), sr["name"], idx,
                        sr["status"], float(sr["duration_ms"]),
                    )
        except Exception as persist_err:
            logger.warning("workflow_run_persist_failed", error=str(persist_err))

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
