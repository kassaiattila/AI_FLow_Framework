"""Process Documentation generation endpoint.

Runs the process_documentation skill in-process (no subprocess fork).
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time as _time
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

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
            export_all,
            extract,
            generate_diagram,
            review,
        )
    except ImportError as e:
        logger.error("skill_import_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Process documentation skill not available: {e}"
        ) from e

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
            step_records.append(
                {"name": step_name, "status": "completed", "duration_ms": elapsed_ms}
            )
    except Exception as e:
        run_status = "failed"
        run_error = str(e)
        logger.error("generate_process_doc_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        total_duration_ms = int((_time.perf_counter() - run_start) * 1000)
        # Estimate BPMN generation cost: 4 LLM calls, ~2K input + 1K output tokens each
        _estimated_bpmn_cost = 0.0
        try:
            from aiflow.models.cost import ModelCostCalculator

            calc = ModelCostCalculator()
            # 4 steps use LLM: classify, elaborate, extract, review (~2000 in, 1000 out each)
            _estimated_bpmn_cost = calc.calculate("openai/gpt-4o", 8000, 4000)
            from aiflow.api.cost_recorder import record_cost

            await record_cost(
                workflow_run_id=run_id,
                step_name="bpmn_generation",
                model="openai/gpt-4o",
                input_tokens=8000,
                output_tokens=4000,
                cost_usd=_estimated_bpmn_cost,
            )
        except Exception:
            pass
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
                    uuid.UUID(run_id),
                    "bpmn_generation",
                    "1.0",
                    "process_documentation",
                    run_status,
                    json.dumps({"user_input": request.user_input[:100]}),
                    float(total_duration_ms),
                    _estimated_bpmn_cost,
                    run_error,
                )
                for idx, sr in enumerate(step_records):
                    await conn.execute(
                        """INSERT INTO step_runs
                           (id, workflow_run_id, step_name, step_index, status, duration_ms)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        uuid.uuid4(),
                        uuid.UUID(run_id),
                        sr["name"],
                        idx,
                        sr["status"],
                        float(sr["duration_ms"]),
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


# ---------------------------------------------------------------------------
# POST /api/v1/process-docs/generate-stream — SSE step-by-step progress
# ---------------------------------------------------------------------------


@router.post("/generate-stream")
async def generate_process_doc_stream(request: GenerateRequest) -> StreamingResponse:
    """Generate BPMN diagram with real-time SSE step progress.

    Events: init, file_start, file_step, file_done, complete, error.
    Uses the same per-file event format as Documents and RAG for UI consistency.
    """
    if not request.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input is required")

    output_dir = Path(tempfile.mkdtemp(prefix="aiflow_procdoc_"))

    try:
        from skills.process_documentation.workflow import (
            classify_intent,
            elaborate,
            export_all,
            extract,
            generate_diagram,
            review,
        )
    except ImportError as e:
        err_msg = str(e)
        logger.error("skill_import_failed", error=err_msg)

        async def err():
            yield f"data: {json.dumps({'event': 'error', 'error': err_msg})}\n\n"

        return StreamingResponse(err(), media_type="text/event-stream")

    pipeline = [
        ("classify", classify_intent),
        ("elaborate", elaborate),
        ("extract", extract),
        ("review", review),
        ("generate", generate_diagram),
        ("export", export_all),
    ]
    step_names = [s[0] for s in pipeline]

    async def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        # Use the per-file event format with a single "file" for UI consistency
        fname = "BPMN Diagram"
        yield sse({"event": "init", "total_files": 1, "steps": step_names})
        yield sse({"event": "file_start", "file": fname, "file_index": 0, "total_files": 1})
        await asyncio.sleep(0)

        run_id = str(uuid.uuid4())
        run_start = _time.perf_counter()
        step_records: list[dict[str, Any]] = []
        data: dict[str, Any] = {"user_input": request.user_input, "output_dir": str(output_dir)}

        for si, (name, step_fn) in enumerate(pipeline):
            yield sse(
                {
                    "event": "file_step",
                    "file": fname,
                    "file_index": 0,
                    "step_index": si,
                    "step_name": name,
                    "status": "running",
                }
            )
            await asyncio.sleep(0)
            t = _time.perf_counter()
            try:
                data = await step_fn(data)
                elapsed_ms = int((_time.perf_counter() - t) * 1000)
                step_records.append(
                    {"name": name, "status": "completed", "duration_ms": elapsed_ms}
                )
                yield sse(
                    {
                        "event": "file_step",
                        "file": fname,
                        "file_index": 0,
                        "step_index": si,
                        "step_name": name,
                        "status": "done",
                        "elapsed_ms": elapsed_ms,
                    }
                )
            except Exception as e:
                elapsed_ms = int((_time.perf_counter() - t) * 1000)
                step_records.append({"name": name, "status": "failed", "duration_ms": elapsed_ms})
                logger.error("generate_stream_step_failed", step=name, error=str(e))
                yield sse(
                    {
                        "event": "file_error",
                        "file": fname,
                        "file_index": 0,
                        "step_name": name,
                        "error": str(e),
                    }
                )
                yield sse({"event": "file_done", "file": fname, "file_index": 0, "ok": False})
                yield sse(
                    {"event": "complete", "mermaid_code": "", "review": None, "error": str(e)}
                )
                return

        yield sse({"event": "file_done", "file": fname, "file_index": 0, "ok": True})

        total_duration_ms = int((_time.perf_counter() - run_start) * 1000)

        # Read generated mermaid code
        mermaid_code = data.get("mermaid_code", "")
        if not mermaid_code:
            mmd_file = output_dir / "diagram.mmd"
            if mmd_file.exists():
                mermaid_code = mmd_file.read_text(encoding="utf-8")

        # Persist workflow run + cost (best-effort)
        try:
            from aiflow.api.cost_recorder import record_cost
            from aiflow.models.cost import ModelCostCalculator

            calc = ModelCostCalculator()
            cost = calc.calculate("openai/gpt-4o", 8000, 4000)
            await record_cost(
                workflow_run_id=run_id,
                step_name="bpmn_generation",
                model="openai/gpt-4o",
                input_tokens=8000,
                output_tokens=4000,
                cost_usd=cost,
            )
        except Exception:
            pass
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO workflow_runs
                       (id, workflow_name, workflow_version, skill_name, status, input_data,
                        started_at, completed_at, total_duration_ms, total_cost_usd, error)
                       VALUES ($1,$2,$3,$4,$5,$6, NOW()-MAKE_INTERVAL(secs:=$7::float/1000), NOW(),$7,$8,$9)""",
                    uuid.UUID(run_id),
                    "bpmn_generation",
                    "1.0",
                    "process_documentation",
                    "completed",
                    json.dumps({"user_input": request.user_input[:100]}),
                    float(total_duration_ms),
                    0.0,
                    None,
                )
                for idx, sr in enumerate(step_records):
                    await conn.execute(
                        "INSERT INTO step_runs (id,workflow_run_id,step_name,step_index,status,duration_ms) VALUES ($1,$2,$3,$4,$5,$6)",
                        uuid.uuid4(),
                        uuid.UUID(run_id),
                        sr["name"],
                        idx,
                        sr["status"],
                        float(sr["duration_ms"]),
                    )
        except Exception as e:
            logger.warning("workflow_run_persist_failed", error=str(e))

        yield sse({"event": "complete", "mermaid_code": mermaid_code, "review": data.get("review")})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
