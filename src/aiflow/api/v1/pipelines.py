"""Pipeline orchestrator API — CRUD, run, validate, adapters."""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool, get_session_factory
from aiflow.pipeline.adapter_base import adapter_registry
from aiflow.pipeline.adapters import discover_adapters
from aiflow.pipeline.compiler import PipelineCompileError, PipelineCompiler
from aiflow.pipeline.parser import PipelineParseError, PipelineParser
from aiflow.pipeline.runner import PipelineRunner
from aiflow.pipeline.schema import PipelineDefinition

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])

# Ensure adapters are discovered
discover_adapters()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PipelineItem(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    enabled: bool = True
    step_count: int = 0
    trigger_type: str = "manual"
    created_at: str | None = None
    updated_at: str | None = None
    created_by: str | None = None


class PipelineListResponse(BaseModel):
    pipelines: list[PipelineItem]
    total: int
    source: str = "backend"


class PipelineDetailResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str = ""
    enabled: bool = True
    yaml_source: str = ""
    definition: dict[str, Any] = Field(default_factory=dict)
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    step_count: int = 0
    steps: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    created_by: str | None = None
    source: str = "backend"


class CreatePipelineRequest(BaseModel):
    yaml_source: str


class UpdatePipelineRequest(BaseModel):
    yaml_source: str | None = None
    description: str | None = None
    enabled: bool | None = None


class RunPipelineRequest(BaseModel):
    input_data: dict[str, Any] = Field(default_factory=dict)


class RunPipelineResponse(BaseModel):
    run_id: str
    pipeline_id: str
    pipeline_name: str
    status: str
    source: str = "backend"


class RunItem(BaseModel):
    id: str
    pipeline_id: str | None = None
    workflow_name: str = ""
    status: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    total_duration_ms: float | None = None
    error: str | None = None


class RunListResponse(BaseModel):
    runs: list[RunItem]
    total: int
    source: str = "backend"


class RunDetailResponse(BaseModel):
    id: str
    pipeline_id: str | None = None
    workflow_name: str = ""
    status: str = ""
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    total_duration_ms: float | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "backend"


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    step_count: int = 0
    adapters_available: dict[str, bool] = Field(default_factory=dict)
    source: str = "backend"


class AdapterItem(BaseModel):
    service_name: str
    method_name: str
    input_schema: str = ""
    output_schema: str = ""


class AdaptersListResponse(BaseModel):
    adapters: list[AdapterItem]
    total: int
    source: str = "backend"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_pipelines(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    enabled_only: bool = Query(False),
) -> PipelineListResponse:
    """List all pipeline definitions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        where = "WHERE enabled = true" if enabled_only else ""
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM pipeline_definitions {where}"
        )
        rows = await conn.fetch(
            f"""SELECT id, name, version, description, enabled,
                       definition, trigger_config, created_at, updated_at, created_by
                FROM pipeline_definitions {where}
                ORDER BY updated_at DESC
                LIMIT $1 OFFSET $2""",
            limit,
            offset,
        )

    pipelines = []
    for r in rows:
        defn = r["definition"] or {}
        if isinstance(defn, str):
            defn = json.loads(defn)
        steps = defn.get("steps", [])
        trigger = r["trigger_config"] or {}
        if isinstance(trigger, str):
            trigger = json.loads(trigger)
        pipelines.append(
            PipelineItem(
                id=str(r["id"]),
                name=r["name"],
                version=r["version"],
                description=r["description"] or "",
                enabled=r["enabled"],
                step_count=len(steps),
                trigger_type=trigger.get("type", "manual"),
                created_at=str(r["created_at"]) if r["created_at"] else None,
                updated_at=str(r["updated_at"]) if r["updated_at"] else None,
                created_by=r["created_by"],
            )
        )

    return PipelineListResponse(pipelines=pipelines, total=total)


@router.post("", status_code=201)
async def create_pipeline(req: CreatePipelineRequest) -> PipelineDetailResponse:
    """Create a new pipeline from YAML source."""
    parser = PipelineParser()
    try:
        pipeline_def = parser.parse_yaml(req.yaml_source)
    except PipelineParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    defn_dict = pipeline_def.model_dump(mode="json")
    trigger_dict = defn_dict.get("trigger", {})
    input_schema = defn_dict.get("input_schema", {})

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM pipeline_definitions WHERE name=$1 AND version=$2",
            pipeline_def.name,
            pipeline_def.version,
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Pipeline '{pipeline_def.name}' v{pipeline_def.version} already exists",
            )

        row = await conn.fetchrow(
            """INSERT INTO pipeline_definitions
               (name, version, description, yaml_source, definition,
                trigger_config, input_schema, enabled)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, true)
               RETURNING id, created_at, updated_at""",
            pipeline_def.name,
            pipeline_def.version,
            pipeline_def.description,
            req.yaml_source,
            json.dumps(defn_dict),
            json.dumps(trigger_dict),
            json.dumps(input_schema),
        )

    steps_info = [
        {"name": s.name, "service": s.service, "method": s.method}
        for s in pipeline_def.steps
    ]

    return PipelineDetailResponse(
        id=str(row["id"]),
        name=pipeline_def.name,
        version=pipeline_def.version,
        description=pipeline_def.description,
        yaml_source=req.yaml_source,
        definition=defn_dict,
        trigger_config=trigger_dict,
        input_schema=input_schema,
        step_count=len(pipeline_def.steps),
        steps=steps_info,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("/adapters")
async def list_adapters() -> AdaptersListResponse:
    """List all registered pipeline adapters."""
    pairs = adapter_registry.list_adapters()
    items = [
        AdapterItem(
            service_name=svc,
            method_name=method,
            input_schema=adapter_registry.get(svc, method).input_schema.__name__,
            output_schema=adapter_registry.get(svc, method).output_schema.__name__,
        )
        for svc, method in pairs
    ]
    return AdaptersListResponse(adapters=items, total=len(items))


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str) -> PipelineDetailResponse:
    """Get pipeline definition detail."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, name, version, description, yaml_source, definition,
                      trigger_config, input_schema, enabled, created_at,
                      updated_at, created_by
               FROM pipeline_definitions WHERE id = $1""",
            uuid.UUID(pipeline_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    defn = row["definition"] or {}
    if isinstance(defn, str):
        defn = json.loads(defn)
    steps = defn.get("steps", [])
    trigger = row["trigger_config"] or {}
    if isinstance(trigger, str):
        trigger = json.loads(trigger)
    inp_schema = row["input_schema"] or {}
    if isinstance(inp_schema, str):
        inp_schema = json.loads(inp_schema)

    steps_info = [
        {"name": s.get("name", ""), "service": s.get("service", ""), "method": s.get("method", "")}
        for s in steps
    ]

    return PipelineDetailResponse(
        id=str(row["id"]),
        name=row["name"],
        version=row["version"],
        description=row["description"] or "",
        enabled=row["enabled"],
        yaml_source=row["yaml_source"],
        definition=defn,
        trigger_config=trigger,
        input_schema=inp_schema,
        step_count=len(steps),
        steps=steps_info,
        created_at=str(row["created_at"]) if row["created_at"] else None,
        updated_at=str(row["updated_at"]) if row["updated_at"] else None,
        created_by=row["created_by"],
    )


@router.put("/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str, req: UpdatePipelineRequest
) -> PipelineDetailResponse:
    """Update an existing pipeline."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        updates = ["updated_at = NOW()"]
        params: list[Any] = []
        idx = 1

        if req.yaml_source is not None:
            parser = PipelineParser()
            try:
                pipeline_def = parser.parse_yaml(req.yaml_source)
            except PipelineParseError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            defn_dict = pipeline_def.model_dump(mode="json")
            params.extend([
                req.yaml_source,
                json.dumps(defn_dict),
                pipeline_def.name,
                pipeline_def.version,
                pipeline_def.description,
            ])
            updates.extend([
                f"yaml_source = ${idx}",
                f"definition = ${idx + 1}::jsonb",
                f"name = ${idx + 2}",
                f"version = ${idx + 3}",
                f"description = ${idx + 4}",
            ])
            idx += 5

        if req.description is not None and req.yaml_source is None:
            params.append(req.description)
            updates.append(f"description = ${idx}")
            idx += 1

        if req.enabled is not None:
            params.append(req.enabled)
            updates.append(f"enabled = ${idx}")
            idx += 1

        params.append(uuid.UUID(pipeline_id))
        set_clause = ", ".join(updates)
        await conn.execute(
            f"UPDATE pipeline_definitions SET {set_clause} WHERE id = ${idx}",
            *params,
        )

    return await get_pipeline(pipeline_id)


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(pipeline_id: str) -> None:
    """Delete a pipeline definition."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted = await conn.execute(
            "DELETE FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
    if deleted == "DELETE 0":
        raise HTTPException(status_code=404, detail="Pipeline not found")


@router.post("/{pipeline_id}/validate")
async def validate_pipeline(pipeline_id: str) -> ValidateResponse:
    """Validate a pipeline's YAML and check adapter availability."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT yaml_source, definition FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    parser = PipelineParser()
    errors: list[str] = []
    try:
        pipeline_def = parser.parse_yaml(row["yaml_source"])
    except PipelineParseError as exc:
        return ValidateResponse(valid=False, errors=[str(exc)])

    compiler = PipelineCompiler(adapter_registry)
    adapters_ok: dict[str, bool] = {}
    for step in pipeline_def.steps:
        key = f"{step.service}.{step.method}"
        adapters_ok[key] = adapter_registry.has(step.service, step.method)
        if not adapters_ok[key]:
            errors.append(f"Missing adapter: {key}")

    try:
        compiler.compile(pipeline_def)
    except PipelineCompileError as exc:
        errors.append(str(exc))

    return ValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        step_count=len(pipeline_def.steps),
        adapters_available=adapters_ok,
    )


@router.post("/{pipeline_id}/run", status_code=202)
async def run_pipeline(
    pipeline_id: str, req: RunPipelineRequest
) -> RunPipelineResponse:
    """Execute a pipeline synchronously and return the run result.

    Returns 202 Accepted with run_id and final status.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, enabled FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if not row["enabled"]:
        raise HTTPException(status_code=400, detail="Pipeline is disabled")

    session_factory = await get_session_factory()
    runner = PipelineRunner(adapter_registry, session_factory)

    try:
        result = await runner.run(
            pipeline_id=uuid.UUID(pipeline_id),
            input_data=req.input_data,
        )
    except Exception as exc:
        logger.error("pipeline_run_failed", pipeline_id=pipeline_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {exc}")

    return RunPipelineResponse(
        run_id=str(result.run_id),
        pipeline_id=pipeline_id,
        pipeline_name=result.pipeline_name,
        status=result.status,
    )


@router.get("/{pipeline_id}/runs")
async def list_pipeline_runs(
    pipeline_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> RunListResponse:
    """List execution history for a pipeline."""
    pool = await get_pool()
    pid = uuid.UUID(pipeline_id)
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM workflow_runs WHERE pipeline_id = $1",
            pid,
        )
        rows = await conn.fetch(
            """SELECT id, pipeline_id, workflow_name, status,
                      started_at, completed_at, total_duration_ms, error
               FROM workflow_runs WHERE pipeline_id = $1
               ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
            pid,
            limit,
            offset,
        )

    runs = [
        RunItem(
            id=str(r["id"]),
            pipeline_id=str(r["pipeline_id"]) if r["pipeline_id"] else None,
            workflow_name=r["workflow_name"],
            status=r["status"],
            started_at=str(r["started_at"]) if r["started_at"] else None,
            completed_at=str(r["completed_at"]) if r["completed_at"] else None,
            total_duration_ms=r["total_duration_ms"],
            error=r["error"],
        )
        for r in rows
    ]
    return RunListResponse(runs=runs, total=total)


@router.get("/{pipeline_id}/runs/{run_id}")
async def get_pipeline_run(pipeline_id: str, run_id: str) -> RunDetailResponse:
    """Get detailed info for a specific pipeline run."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, pipeline_id, workflow_name, status, input_data,
                      output_data, error, started_at, completed_at, total_duration_ms
               FROM workflow_runs WHERE id = $1 AND pipeline_id = $2""",
            uuid.UUID(run_id),
            uuid.UUID(pipeline_id),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")

        step_rows = await conn.fetch(
            """SELECT step_name, status, input_data, output_data, error,
                      started_at, completed_at, duration_ms
               FROM step_runs WHERE workflow_run_id = $1
               ORDER BY step_index""",
            uuid.UUID(run_id),
        )

    input_data = row["input_data"] or {}
    if isinstance(input_data, str):
        input_data = json.loads(input_data)
    output_data = row["output_data"]
    if isinstance(output_data, str):
        output_data = json.loads(output_data)

    steps = [
        {
            "step_name": s["step_name"],
            "status": s["status"],
            "duration_ms": s["duration_ms"],
            "error": s["error"],
            "started_at": str(s["started_at"]) if s["started_at"] else None,
            "completed_at": str(s["completed_at"]) if s["completed_at"] else None,
        }
        for s in step_rows
    ]

    return RunDetailResponse(
        id=str(row["id"]),
        pipeline_id=str(row["pipeline_id"]) if row["pipeline_id"] else None,
        workflow_name=row["workflow_name"],
        status=row["status"],
        input_data=input_data,
        output_data=output_data,
        error=row["error"],
        started_at=str(row["started_at"]) if row["started_at"] else None,
        completed_at=str(row["completed_at"]) if row["completed_at"] else None,
        total_duration_ms=row["total_duration_ms"],
        steps=steps,
    )


@router.get("/{pipeline_id}/yaml")
async def export_pipeline_yaml(pipeline_id: str) -> dict[str, str]:
    """Export pipeline as raw YAML."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT yaml_source FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"yaml_source": row["yaml_source"], "source": "backend"}


# ---------------------------------------------------------------------------
# Template endpoints (C19)
# ---------------------------------------------------------------------------


class TemplateItem(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    step_count: int = 0
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    file_name: str = ""


class TemplateListResponse(BaseModel):
    templates: list[TemplateItem]
    total: int
    source: str = "backend"


class TemplateDetailResponse(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    step_count: int = 0
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    yaml_source: str = ""
    source: str = "backend"


class DeployTemplateResponse(BaseModel):
    id: str
    name: str
    version: str
    source: str = "backend"


@router.get("/templates/list", response_model=TemplateListResponse)
async def list_templates() -> TemplateListResponse:
    """List all built-in pipeline templates."""
    from aiflow.pipeline.templates import TemplateRegistry

    registry = TemplateRegistry()
    templates = registry.list_all()

    items = [
        TemplateItem(
            name=t.name,
            version=t.version,
            description=t.description,
            step_count=t.step_count,
            tags=t.tags,
            category=t.category,
            file_name=t.file_name,
        )
        for t in templates
    ]

    return TemplateListResponse(templates=items, total=len(items))


@router.get("/templates/{name}", response_model=TemplateDetailResponse)
async def get_template(name: str) -> TemplateDetailResponse:
    """Get a specific template with full YAML source."""
    from aiflow.pipeline.templates import TemplateRegistry

    registry = TemplateRegistry()
    info = registry.get(name)
    if info is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{name}' not found",
        )

    yaml_source = registry.get_yaml(name) or ""

    return TemplateDetailResponse(
        name=info.name,
        version=info.version,
        description=info.description,
        step_count=info.step_count,
        tags=info.tags,
        category=info.category,
        yaml_source=yaml_source,
    )


@router.post(
    "/templates/{name}/deploy",
    response_model=DeployTemplateResponse,
    status_code=201,
)
async def deploy_template(name: str) -> DeployTemplateResponse:
    """Deploy a built-in template as a new pipeline definition."""
    from aiflow.pipeline.templates import TemplateRegistry

    registry = TemplateRegistry()
    yaml_source = registry.get_yaml(name)
    if yaml_source is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{name}' not found",
        )

    # Parse the template YAML
    parser = PipelineParser()
    try:
        pipeline_def = parser.parse_yaml(yaml_source)
    except PipelineParseError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Template YAML invalid: {exc}",
        )

    defn_dict = pipeline_def.model_dump(mode="json")
    trigger_dict = defn_dict.get("trigger", {})
    input_schema = defn_dict.get("input_schema", {})

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM pipeline_definitions WHERE name=$1 AND version=$2",
            pipeline_def.name,
            pipeline_def.version,
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Pipeline '{pipeline_def.name}' "
                    f"v{pipeline_def.version} already exists"
                ),
            )

        row = await conn.fetchrow(
            """INSERT INTO pipeline_definitions
               (name, version, description, yaml_source, definition,
                trigger_config, input_schema, enabled)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, true)
               RETURNING id""",
            pipeline_def.name,
            pipeline_def.version,
            pipeline_def.description,
            yaml_source,
            json.dumps(defn_dict),
            json.dumps(trigger_dict),
            json.dumps(input_schema),
        )

    return DeployTemplateResponse(
        id=str(row["id"]),  # type: ignore[index]
        name=pipeline_def.name,
        version=pipeline_def.version,
    )
