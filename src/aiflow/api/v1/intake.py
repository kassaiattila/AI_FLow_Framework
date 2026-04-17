"""Intake upload-package router — canonical push-mode HTTP entry point.

Source: 01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md Day 13 (E3.2),
        101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N3/N4.

Endpoint: ``POST /api/v1/intake/upload-package`` (multipart/form-data).

Accepts N files + M free-text descriptions in a single upload, runs the N4
associator to compute ``{file_id: description_id}`` mappings, and persists the
resulting ``IntakePackage`` via ``IntakeRepository``. The tenant boundary is
enforced from the JWT (``team_id`` claim, or ``sub`` fallback) — callers must
authenticate with Bearer JWT; API-key auth is accepted but loses the team
scope and falls back to the API key's user_id.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

import asyncpg
import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import BaseModel, Field, ValidationError

from aiflow.api.deps import get_pool
from aiflow.intake.association import resolve_mode_and_associations
from aiflow.intake.exceptions import FileAssociationError
from aiflow.intake.package import (
    AssociationMode,
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.sources._fs import sanitize_filename
from aiflow.state.repositories.intake import IntakeRepository

__all__ = [
    "router",
    "get_intake_repository",
    "get_tenant_id",
    "UploadPackageResponse",
]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/intake", tags=["intake"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_intake_repository() -> IntakeRepository:
    """FastAPI dependency that binds IntakeRepository to the shared asyncpg pool."""
    pool: asyncpg.Pool = await get_pool()
    return IntakeRepository(pool)


def get_tenant_id(request: Request) -> str:
    """Resolve tenant_id from request state (set by AuthMiddleware).

    Preference: JWT ``team_id`` claim > authenticated user_id. AuthMiddleware
    already rejects unauthenticated calls, so reaching this dep without either
    means the endpoint was somehow registered under a public prefix — treat as
    401 defensively.
    """
    team_id = getattr(request.state, "team_id", None)
    if team_id:
        return team_id
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return user_id
    raise HTTPException(status_code=401, detail="Authentication required")


def _get_upload_root() -> Path:
    """Storage root for multipart uploads. Override via AIFLOW_INTAKE_UPLOAD_ROOT."""
    return Path(os.getenv("AIFLOW_INTAKE_UPLOAD_ROOT", "./var/intake/uploads"))


def _get_max_total_bytes() -> int:
    """Aggregate upload cap. Override via AIFLOW_INTAKE_UPLOAD_MAX_BYTES (default 50 MB)."""
    raw = os.getenv("AIFLOW_INTAKE_UPLOAD_MAX_BYTES", "").strip()
    return int(raw) if raw else 50 * 1024 * 1024


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class UploadPackageFile(BaseModel):
    """File entry in the response — sanitized view of IntakeFile."""

    file_id: UUID
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    sequence_index: int | None = None


class UploadPackageDescription(BaseModel):
    """Description entry in the response."""

    description_id: UUID
    text: str
    role: DescriptionRole
    language: str | None = None
    associated_file_ids: list[UUID] = Field(default_factory=list)


class UploadPackageResponse(BaseModel):
    """Success envelope for a created intake package."""

    package_id: UUID
    tenant_id: str
    source_type: IntakeSourceType
    status: str
    association_mode: AssociationMode | None = None
    file_count: int
    description_count: int
    files: list[UploadPackageFile] = Field(default_factory=list)
    descriptions: list[UploadPackageDescription] = Field(default_factory=list)


class UploadPackageErrorResponse(BaseModel):
    """Error envelope for 4xx responses."""

    detail: str


_RESPONSES: dict[int | str, dict[str, object]] = {
    201: {
        "description": "Upload accepted and persisted as IntakePackage.",
        "model": UploadPackageResponse,
    },
    400: {
        "description": "Malformed request (bad JSON, no files, missing fields).",
        "model": UploadPackageErrorResponse,
    },
    401: {
        "description": "Missing or invalid authentication.",
        "model": UploadPackageErrorResponse,
    },
    413: {
        "description": "Aggregate upload size exceeds max_total_bytes.",
        "model": UploadPackageErrorResponse,
    },
    422: {
        "description": "Association layer rejected the package (mode/rules mismatch).",
        "model": UploadPackageErrorResponse,
    },
}


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------


def _parse_json_field(raw: str | None, field_name: str, *, default: Any) -> Any:
    """Parse a JSON form field. 400 on malformed JSON."""
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is not valid JSON: {exc.msg}",
        ) from None


def _parse_association_mode(raw: str | None) -> AssociationMode | None:
    if raw is None or raw == "":
        return None
    try:
        return AssociationMode(raw)
    except ValueError as exc:
        valid = ", ".join(m.value for m in AssociationMode)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid association_mode={raw!r}; expected one of: {valid}",
        ) from exc


def _build_descriptions(raw_list: list[dict[str, Any]]) -> list[IntakeDescription]:
    """Construct IntakeDescription from parsed JSON dicts. 400 on validation failure."""
    descriptions: list[IntakeDescription] = []
    for idx, entry in enumerate(raw_list):
        if not isinstance(entry, dict):
            raise HTTPException(
                status_code=400,
                detail=f"descriptions[{idx}] must be a JSON object",
            )
        try:
            descriptions.append(IntakeDescription(**entry))
        except ValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"descriptions[{idx}] invalid: {exc.errors()[0]['msg']}",
            ) from None
    return descriptions


def _build_filename_rules(
    raw_list: list[dict[str, Any]] | None,
) -> list[tuple[str, UUID]] | None:
    if raw_list is None:
        return None
    rules: list[tuple[str, UUID]] = []
    for idx, entry in enumerate(raw_list):
        if not isinstance(entry, dict) or "pattern" not in entry or "description_id" not in entry:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"filename_rules[{idx}] must be an object with 'pattern' "
                    "and 'description_id' fields"
                ),
            )
        try:
            desc_id = UUID(str(entry["description_id"]))
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"filename_rules[{idx}].description_id is not a valid UUID",
            ) from exc
        pattern = entry["pattern"]
        if not isinstance(pattern, str):
            raise HTTPException(
                status_code=400,
                detail=f"filename_rules[{idx}].pattern must be a string",
            )
        try:
            re.compile(pattern)
        except re.error as exc:
            raise HTTPException(
                status_code=400,
                detail=f"filename_rules[{idx}].pattern is not a valid regex: {exc}",
            ) from exc
        rules.append((pattern, desc_id))
    return rules


def _build_explicit_map(raw: dict[str, Any] | None) -> dict[UUID, UUID] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="explicit_map must be a JSON object")
    result: dict[UUID, UUID] = {}
    for k, v in raw.items():
        try:
            result[UUID(str(k))] = UUID(str(v))
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=400,
                detail="explicit_map keys and values must be valid UUIDs",
            ) from exc
    return result


async def _materialize_files(
    uploads: list[UploadFile],
    *,
    tenant_id: str,
    package_id: UUID,
    max_total_bytes: int,
) -> list[IntakeFile]:
    """Persist uploads under the per-tenant storage root and return IntakeFiles.

    Raises:
        HTTPException(413): Aggregate size exceeds max_total_bytes.
        HTTPException(400): An individual upload is empty (zero bytes).
    """
    pkg_dir = _get_upload_root() / tenant_id / str(package_id)
    pkg_dir.mkdir(parents=True, exist_ok=True)

    files: list[IntakeFile] = []
    running_total = 0
    for index, upload in enumerate(uploads):
        payload = await upload.read()
        size = len(payload)
        if size == 0:
            raise HTTPException(
                status_code=400,
                detail=f"file[{index}] {upload.filename!r} is empty",
            )
        running_total += size
        if running_total > max_total_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Aggregate upload size {running_total} bytes exceeds "
                    f"max_total_bytes={max_total_bytes}"
                ),
            )
        raw_name = upload.filename or f"upload_{index}.bin"
        safe = sanitize_filename(raw_name)
        dest = pkg_dir / safe
        if dest.exists():
            dest = pkg_dir / f"{uuid4().hex}_{safe}"
        dest.write_bytes(payload)
        mime = upload.content_type or "application/octet-stream"
        files.append(
            IntakeFile(
                file_path=str(dest),
                file_name=raw_name,
                mime_type=mime,
                size_bytes=size,
                sha256=hashlib.sha256(payload).hexdigest(),
                sequence_index=index,
                source_metadata={"sanitized_filename": safe, "upload_index": index},
            )
        )
    return files


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------


@router.post(
    "/upload-package",
    status_code=201,
    response_model=UploadPackageResponse,
    responses=_RESPONSES,
    summary="Upload N files + M descriptions as a single IntakePackage",
    description=(
        "Multipart/form-data endpoint for push-mode ingestion. The caller sends "
        "one or more ``files`` parts plus an optional JSON-encoded "
        "``descriptions`` list and association controls. The N4 associator "
        "computes ``{file_id: description_id}`` mappings; the chosen "
        "``AssociationMode`` is persisted. tenant_id is resolved from the "
        "JWT ``team_id`` claim (or ``sub`` as fallback) — never from form fields."
    ),
)
async def upload_package(
    files: Annotated[list[UploadFile], File(description="One or more files to ingest.")],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[IntakeRepository, Depends(get_intake_repository)],
    descriptions: Annotated[
        str,
        Form(
            description=(
                "JSON-encoded list of description objects (text, role, language, ...). "
                "Defaults to ``[]``."
            ),
        ),
    ] = "[]",
    association_mode: Annotated[
        str | None,
        Form(
            description=(
                "Force a specific association mode (explicit | filename_match | "
                "order | single_description). Omit for auto-detect."
            ),
        ),
    ] = None,
    filename_rules: Annotated[
        str | None,
        Form(
            description=(
                'JSON array of filename rules: ``[{"pattern": <regex>, '
                '"description_id": <uuid>}, ...]``.'
            ),
        ),
    ] = None,
    explicit_map: Annotated[
        str | None,
        Form(
            description=(
                "JSON object mapping ``file_id -> description_id``. Only used "
                "when association_mode=explicit (rare from browsers)."
            ),
        ),
    ] = None,
) -> UploadPackageResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    descriptions_raw = _parse_json_field(descriptions, "descriptions", default=[])
    if not isinstance(descriptions_raw, list):
        raise HTTPException(status_code=400, detail="descriptions must be a JSON array")
    description_models = _build_descriptions(descriptions_raw)

    filename_rules_raw = _parse_json_field(filename_rules, "filename_rules", default=None)
    if filename_rules_raw is not None and not isinstance(filename_rules_raw, list):
        raise HTTPException(status_code=400, detail="filename_rules must be a JSON array")
    rules = _build_filename_rules(filename_rules_raw)

    explicit_map_raw = _parse_json_field(explicit_map, "explicit_map", default=None)
    explicit = _build_explicit_map(explicit_map_raw)

    mode = _parse_association_mode(association_mode)

    package_id = uuid4()
    intake_files = await _materialize_files(
        files,
        tenant_id=tenant_id,
        package_id=package_id,
        max_total_bytes=_get_max_total_bytes(),
    )

    try:
        package = IntakePackage(
            package_id=package_id,
            source_type=IntakeSourceType.FILE_UPLOAD,
            tenant_id=tenant_id,
            files=intake_files,
            descriptions=description_models,
            source_metadata={"upload_file_count": len(intake_files)},
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"IntakePackage validation failed: {exc.errors()[0]['msg']}",
        ) from None

    try:
        resolve_mode_and_associations(
            package,
            forced_mode=mode,
            filename_rules=rules,
            explicit_map=explicit,
        )
    except FileAssociationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    await repo.insert_package(package)
    logger.info(
        "intake_upload_package_created",
        package_id=str(package.package_id),
        tenant_id=tenant_id,
        file_count=len(package.files),
        description_count=len(package.descriptions),
        association_mode=(package.association_mode.value if package.association_mode else None),
    )
    return _build_response(package)


def _build_response(package: IntakePackage) -> UploadPackageResponse:
    return UploadPackageResponse(
        package_id=package.package_id,
        tenant_id=package.tenant_id,
        source_type=package.source_type,
        status=package.status.value,
        association_mode=package.association_mode,
        file_count=len(package.files),
        description_count=len(package.descriptions),
        files=[
            UploadPackageFile(
                file_id=f.file_id,
                file_name=f.file_name,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes,
                sha256=f.sha256,
                sequence_index=f.sequence_index,
            )
            for f in package.files
        ],
        descriptions=[
            UploadPackageDescription(
                description_id=d.description_id,
                text=d.text,
                role=d.role,
                language=d.language,
                associated_file_ids=list(d.associated_file_ids),
            )
            for d in package.descriptions
        ],
    )
