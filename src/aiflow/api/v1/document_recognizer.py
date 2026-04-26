"""Document Recognizer API router — Sprint V SV-3.

5 routes mounted under ``/api/v1/document-recognizer``:

* ``POST /recognize``                      — multipart upload + run pipeline
* ``GET  /doctypes``                       — list (tenant-aware merged view)
* ``GET  /doctypes/{name}``                — single descriptor detail
* ``PUT  /doctypes/{name}``                — operator per-tenant override creation
* ``DELETE /doctypes/{name}``              — remove tenant override

The recognize route is the only one that runs the full pipeline (parse →
classify → extract → intent_routing → audit). The doctype CRUD endpoints
are operator-facing — they let a tenant maintain its own descriptor
overrides at ``data/doctypes/_tenant/<tenant_id>/<name>.yaml``.

Cost preflight integration uses the Sprint U S154 ``check_step()`` API
when the descriptor's extraction step has ``metadata.cost_ceiling_usd``;
the per-call/per-tenant ``check()`` API still applies for the LLM
fallback classifier path. SV-3 wires the **API surface**; SV-2's
orchestrator is reused unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Literal

import asyncpg
import structlog
import yaml
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel, Field, ValidationError
from skills.document_recognizer.workflows.recognize_and_extract import (
    get_orchestrator,
)

from aiflow.api.deps import get_pool
from aiflow.api.v1.intake import get_tenant_id
from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocIntentDecision,
    DocRecognitionRequest,
    DocTypeDescriptor,
    DocTypeMatch,
)
from aiflow.services.document_recognizer.classifier import ClassifierInput
from aiflow.services.document_recognizer.repository import DocRecognitionRepository

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/document-recognizer", tags=["document-recognizer"])


# Tenant-name pattern used as a path traversal guard for PUT/DELETE override.
_TENANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_DOCTYPE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class RecognizeResponse(BaseModel):
    """Response shape for ``POST /recognize``."""

    run_id: str = Field(..., description="UUID of the persisted doc_recognition_runs row")
    match: DocTypeMatch
    extraction: DocExtractionResult
    intent: DocIntentDecision
    classification_method: Literal["rule_engine", "llm_fallback", "hint"]
    pii_redacted: bool


class DoctypeListItem(BaseModel):
    """One row in the doctype list."""

    name: str
    display_name: str
    language: str
    category: str
    version: int
    pii_level: Literal["low", "medium", "high"]
    field_count: int
    has_tenant_override: bool


class DoctypeListResponse(BaseModel):
    """Response shape for ``GET /doctypes``."""

    count: int
    items: list[DoctypeListItem]


class DoctypeDetailResponse(BaseModel):
    """Response shape for ``GET /doctypes/{name}``."""

    descriptor: DocTypeDescriptor
    has_tenant_override: bool
    source: Literal["bootstrap", "tenant_override"]


class DoctypeOverrideRequest(BaseModel):
    """Body of ``PUT /doctypes/{name}``: a YAML payload as a string OR a parsed dict."""

    yaml_text: str | None = None
    descriptor: DocTypeDescriptor | None = None

    def resolve(self) -> DocTypeDescriptor:
        if self.descriptor is not None:
            return self.descriptor
        if self.yaml_text:
            try:
                payload = yaml.safe_load(self.yaml_text)
            except yaml.YAMLError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc
            try:
                return DocTypeDescriptor.model_validate(payload)
            except ValidationError as exc:
                raise HTTPException(status_code=400, detail=exc.errors()) from exc
        raise HTTPException(
            status_code=400, detail="Either descriptor or yaml_text must be provided"
        )


class DoctypeOverrideResponse(BaseModel):
    """Response shape for ``PUT /doctypes/{name}``."""

    name: str
    tenant_id: str
    saved_path: str


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _bootstrap_dir() -> Path:
    """Repo-root-relative bootstrap dir; can be overridden via env later."""
    return Path(__file__).resolve().parents[4] / "data" / "doctypes"


def _tenant_overrides_dir() -> Path:
    return _bootstrap_dir() / "_tenant"


def _validate_path_segments(name: str, tenant_id: str) -> None:
    if not _DOCTYPE_NAME_PATTERN.fullmatch(name):
        raise HTTPException(status_code=400, detail=f"Invalid doctype name: {name!r}")
    if not _TENANT_ID_PATTERN.fullmatch(tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant_id")


# ---------------------------------------------------------------------------
# POST /recognize
# ---------------------------------------------------------------------------


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_endpoint(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    file: Annotated[UploadFile, File(description="Document to recognize")],
    doc_type_hint: Annotated[
        str | None,
        Form(description="Optional doc-type hint to short-circuit the rule engine"),
    ] = None,
) -> RecognizeResponse:
    """Run the full recognize_and_extract pipeline + persist audit row.

    SV-3 ships a **simplified parse stage**: we read the upload bytes and
    decode as UTF-8 best-effort. The full document_extractor parser
    routing (docling / Azure DI / unstructured) wires in via the same
    ClassifierInput envelope in a future iteration; SV-3 keeps the API
    surface stable so the admin UI (SV-4) can develop against a clean
    contract.
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty upload")

    # Best-effort text decode (SV-3 simplified parse stage)
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = ""

    ctx = ClassifierInput(
        text=text,
        filename=file.filename,
        mime_type=file.content_type,
        parser_used="upload_bytes_decode",
    )
    # Build the request envelope for symmetry with the contract; SV-3 only
    # uses tenant_id + doc_type_hint downstream (the orchestrator already
    # has the parsed text in ClassifierInput).
    DocRecognitionRequest(
        file_bytes=raw,
        tenant_id=tenant_id,
        doc_type_hint=doc_type_hint,
        filename=file.filename,
    )

    orchestrator = get_orchestrator()
    classification_method: Literal["rule_engine", "llm_fallback", "hint"] = "rule_engine"
    if doc_type_hint:
        classification_method = "hint"

    result = await orchestrator.run(
        ctx,
        tenant_id=tenant_id,
        doc_type_hint=doc_type_hint,
    )
    if result is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "no doc-type matched and no LLM fallback configured — "
                "operator must add descriptors or supply a doc_type hint"
            ),
        )

    match, extraction, intent = result
    descriptor = orchestrator._registry.get_doctype(match.doc_type, tenant_id=tenant_id)  # noqa: SLF001
    pii_redaction = bool(descriptor and descriptor.intent_routing.pii_redaction)

    repository = DocRecognitionRepository(pool)
    run_id = await repository.insert_run(
        tenant_id=tenant_id,
        match=match,
        extraction=extraction,
        intent=intent,
        filename_hint=file.filename,
        classification_method=classification_method,
        pii_redaction=pii_redaction,
    )

    return RecognizeResponse(
        run_id=str(run_id),
        match=match,
        extraction=extraction,
        intent=intent,
        classification_method=classification_method,
        pii_redacted=pii_redaction,
    )


# ---------------------------------------------------------------------------
# GET /doctypes
# ---------------------------------------------------------------------------


@router.get("/doctypes", response_model=DoctypeListResponse)
async def list_doctypes(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> DoctypeListResponse:
    orchestrator = get_orchestrator()
    descriptors = orchestrator._registry.list_doctypes(tenant_id=tenant_id)  # noqa: SLF001

    tenant_dir = _tenant_overrides_dir() / tenant_id
    items: list[DoctypeListItem] = []
    for d in descriptors:
        override_path = tenant_dir / f"{d.name}.yaml"
        items.append(
            DoctypeListItem(
                name=d.name,
                display_name=d.display_name,
                language=d.language,
                category=d.category,
                version=d.version,
                pii_level=d.pii_level,
                field_count=len(d.extraction.fields),
                has_tenant_override=override_path.exists(),
            )
        )
    return DoctypeListResponse(count=len(items), items=items)


# ---------------------------------------------------------------------------
# GET /doctypes/{name}
# ---------------------------------------------------------------------------


@router.get("/doctypes/{name}", response_model=DoctypeDetailResponse)
async def get_doctype(
    name: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> DoctypeDetailResponse:
    if not _DOCTYPE_NAME_PATTERN.fullmatch(name):
        raise HTTPException(status_code=400, detail=f"Invalid doctype name: {name!r}")

    orchestrator = get_orchestrator()
    descriptor = orchestrator._registry.get_doctype(name, tenant_id=tenant_id)  # noqa: SLF001
    if descriptor is None:
        raise HTTPException(status_code=404, detail=f"Doctype not found: {name!r}")

    override_path = _tenant_overrides_dir() / tenant_id / f"{name}.yaml"
    has_override = override_path.exists()
    source: Literal["bootstrap", "tenant_override"] = (
        "tenant_override" if has_override else "bootstrap"
    )

    return DoctypeDetailResponse(
        descriptor=descriptor,
        has_tenant_override=has_override,
        source=source,
    )


# ---------------------------------------------------------------------------
# PUT /doctypes/{name}
# ---------------------------------------------------------------------------


@router.put("/doctypes/{name}", response_model=DoctypeOverrideResponse)
async def upsert_tenant_override(
    name: str,
    body: DoctypeOverrideRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> DoctypeOverrideResponse:
    _validate_path_segments(name, tenant_id)

    descriptor = body.resolve()  # raises HTTP 400 on invalid YAML / Pydantic
    if descriptor.name != name:
        raise HTTPException(
            status_code=400,
            detail=f"descriptor.name {descriptor.name!r} != path {name!r}",
        )

    tenant_dir = _tenant_overrides_dir() / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    target = tenant_dir / f"{name}.yaml"

    payload = descriptor.model_dump_yaml_safe()
    target.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    # Drop registry cache so the next list/get call sees the new override
    orchestrator = get_orchestrator()
    orchestrator._registry.invalidate_cache()  # noqa: SLF001

    logger.info(
        "doc_recognizer.tenant_override_saved",
        tenant_id=tenant_id,
        doctype=name,
        path=str(target),
    )
    return DoctypeOverrideResponse(
        name=name,
        tenant_id=tenant_id,
        saved_path=str(target),
    )


# ---------------------------------------------------------------------------
# DELETE /doctypes/{name}
# ---------------------------------------------------------------------------


@router.delete("/doctypes/{name}", status_code=204)
async def delete_tenant_override(
    name: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> None:
    _validate_path_segments(name, tenant_id)

    target = _tenant_overrides_dir() / tenant_id / f"{name}.yaml"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"No tenant override for {name!r}")

    target.unlink()
    orchestrator = get_orchestrator()
    orchestrator._registry.invalidate_cache()  # noqa: SLF001

    logger.info(
        "doc_recognizer.tenant_override_deleted",
        tenant_id=tenant_id,
        doctype=name,
    )
