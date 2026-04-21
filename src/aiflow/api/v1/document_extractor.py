"""Document extractor read-only viewer endpoints.

Source: 01_PLAN/110_USE_CASE_FIRST_REPLAN.md §4 Sprint I / UC1 session 4 (S97).

Exposes a read-only aggregate view over the v2 IntakePackage pipeline so the
admin UI can render per-package routing + extraction state without any side
effects. Tenant boundary is enforced from the JWT via
:func:`aiflow.api.v1.intake.get_tenant_id`.

Endpoints:
- ``GET /api/v1/document-extractor/packages/{package_id}`` — package +
  files + routing_decisions aggregate.

Note: the ``extraction_results`` surface is not persisted yet (see S97.5
follow-up). The aggregate currently returns ``extractions: []`` — callers
must tolerate an empty list. A separate ``/extractions/{id}`` endpoint is
deliberately NOT registered here; it is queued for S97.5 when
extraction persistence lands.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool
from aiflow.api.v1.intake import get_tenant_id

__all__ = ["router"]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/document-extractor", tags=["document-extractor"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PackageFile(BaseModel):
    """Sanitized view of ``intake_files`` row."""

    file_id: UUID
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    sequence_index: int | None = None


class PackageRoutingDecision(BaseModel):
    """Sanitized view of ``routing_decisions`` row."""

    id: UUID
    file_id: UUID
    chosen_parser: str
    reason: str
    signals: dict[str, Any] = Field(default_factory=dict)
    fallback_chain: list[str] = Field(default_factory=list)
    cost_estimate: float = 0.0
    decided_at: str


class PackageDetailResponse(BaseModel):
    """Aggregate read model for a single IntakePackage."""

    package_id: UUID
    tenant_id: str
    source_type: str
    status: str
    created_at: str
    files: list[PackageFile]
    routing_decisions: list[PackageRoutingDecision]
    extractions: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Persisted extraction results for this package. Always empty in "
            "S97 — extraction persistence lands in S97.5."
        ),
    )
    source: str = "backend"


# ---------------------------------------------------------------------------
# GET /packages/{package_id}
# ---------------------------------------------------------------------------


@router.get("/packages/{package_id}", response_model=PackageDetailResponse)
async def get_package_detail(
    package_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> PackageDetailResponse:
    """Return a read-only aggregate for one IntakePackage.

    Tenant boundary: rows that do not belong to the caller's tenant surface as
    404 (never 403) to avoid leaking existence of cross-tenant ids.
    """
    pool: asyncpg.Pool = await get_pool()
    async with pool.acquire() as conn:
        pkg_row = await conn.fetchrow(
            """
            SELECT package_id, tenant_id, source_type, status, created_at
            FROM intake_packages
            WHERE package_id = $1
            """,
            package_id,
        )

        if pkg_row is None or pkg_row["tenant_id"] != tenant_id:
            logger.info(
                "document_extractor_package_not_found",
                package_id=str(package_id),
                tenant_id=tenant_id,
                found=pkg_row is not None,
            )
            raise HTTPException(status_code=404, detail="Package not found")

        file_rows = await conn.fetch(
            """
            SELECT file_id, file_name, mime_type, size_bytes, sha256,
                   sequence_index
            FROM intake_files
            WHERE package_id = $1
            ORDER BY sequence_index NULLS LAST, file_name
            """,
            package_id,
        )
        decision_rows = await conn.fetch(
            """
            SELECT id, file_id, chosen_parser, reason, signals,
                   fallback_chain, cost_estimate, decided_at
            FROM routing_decisions
            WHERE package_id = $1 AND tenant_id = $2
            ORDER BY decided_at
            """,
            package_id,
            tenant_id,
        )

    return PackageDetailResponse(
        package_id=pkg_row["package_id"],
        tenant_id=pkg_row["tenant_id"],
        source_type=pkg_row["source_type"],
        status=pkg_row["status"],
        created_at=pkg_row["created_at"].isoformat(),
        files=[
            PackageFile(
                file_id=fr["file_id"],
                file_name=fr["file_name"],
                mime_type=fr["mime_type"],
                size_bytes=fr["size_bytes"],
                sha256=fr["sha256"],
                sequence_index=fr["sequence_index"],
            )
            for fr in file_rows
        ],
        routing_decisions=[
            PackageRoutingDecision(
                id=dr["id"],
                file_id=dr["file_id"],
                chosen_parser=dr["chosen_parser"],
                reason=dr["reason"],
                signals=_parse_jsonb(dr["signals"]),
                fallback_chain=_parse_jsonb(dr["fallback_chain"]) or [],
                cost_estimate=float(dr["cost_estimate"]),
                decided_at=dr["decided_at"].isoformat(),
            )
            for dr in decision_rows
        ],
        extractions=[],
    )


def _parse_jsonb(value: object) -> Any:
    """Normalize a JSONB column that asyncpg may deliver as str or native."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        import json

        return json.loads(value)
    return value
