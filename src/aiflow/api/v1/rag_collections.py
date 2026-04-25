"""Admin RAG collections API (Sprint S / S144).

Operator surface for the multi-tenant + multi-profile vector DB model
introduced by Alembic 046 (S143). Three endpoints:

* ``GET  /api/v1/rag-collections``                          — paged list, optional ``tenant_id`` filter
* ``GET  /api/v1/rag-collections/{collection_id}``          — single-collection detail
* ``PATCH /api/v1/rag-collections/{collection_id}/embedder-profile``
                                                            — attach / detach embedder profile,
                                                              409 on dim-mismatch

Path note: the legacy ``rag_engine`` router already owns
``/api/v1/rag/collections`` for ingest/query/feedback flows. To preserve
backward compatibility for the existing UC2 RAG UI page (Sprint J S102),
this admin surface lives at the hyphenated sibling path
``/api/v1/rag-collections``. See PR description for details.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aiflow.services.rag_engine.service import (
    DimensionMismatch,
    UnknownEmbedderProfile,
)

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/rag-collections", tags=["rag-collections"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RagCollectionListItem(BaseModel):
    """One row in the admin listing — minimum the table needs."""

    id: str
    name: str
    tenant_id: str = "default"
    embedder_profile_id: str | None = None
    embedding_dim: int = 1536
    chunk_count: int = 0
    document_count: int = 0
    updated_at: str | None = None


class RagCollectionListResponse(BaseModel):
    items: list[RagCollectionListItem]
    total: int
    source: str = "backend"


class RagCollectionDetailResponse(BaseModel):
    """Detail-pane payload — list row plus descriptive fields."""

    id: str
    name: str
    tenant_id: str = "default"
    embedder_profile_id: str | None = None
    embedding_dim: int = 1536
    chunk_count: int = 0
    document_count: int = 0
    updated_at: str | None = None
    description: str | None = None
    language: str = "hu"
    embedding_model: str = "openai/text-embedding-3-small"
    created_at: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    source: str = "backend"


class RagCollectionEmbedderProfileUpdate(BaseModel):
    """Body for the PATCH …/embedder-profile route."""

    embedder_profile_id: str | None = None


# ---------------------------------------------------------------------------
# Service factory (mirrors rag_engine router pattern)
# ---------------------------------------------------------------------------


async def _get_service():
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from aiflow.api.deps import get_engine
    from aiflow.services.rag_engine import RAGEngineConfig, RAGEngineService

    engine = await get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    service = RAGEngineService(session_factory=session_factory, config=RAGEngineConfig())
    await service.start()
    return service


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=RagCollectionListResponse)
async def list_collections(
    tenant_id: str | None = Query(default=None, description="Filter by tenant_id"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> RagCollectionListResponse:
    """List collections, optionally filtered by ``tenant_id``."""
    svc = await _get_service()
    try:
        collections = await svc.list_collections()
    except Exception as exc:  # noqa: BLE001
        logger.error("rag_collections_list_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if tenant_id:
        collections = [c for c in collections if c.tenant_id == tenant_id]

    total = len(collections)
    page = collections[offset : offset + limit]

    items = [
        RagCollectionListItem(
            id=c.id,
            name=c.name,
            tenant_id=c.tenant_id,
            embedder_profile_id=c.embedder_profile_id,
            embedding_dim=c.embedding_dim,
            chunk_count=c.chunk_count,
            document_count=c.document_count,
            updated_at=c.updated_at,
        )
        for c in page
    ]
    return RagCollectionListResponse(items=items, total=total)


@router.get("/{collection_id}", response_model=RagCollectionDetailResponse)
async def get_collection(collection_id: str) -> RagCollectionDetailResponse:
    """Return one collection's full admin detail."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return RagCollectionDetailResponse(
        id=coll.id,
        name=coll.name,
        tenant_id=coll.tenant_id,
        embedder_profile_id=coll.embedder_profile_id,
        embedding_dim=coll.embedding_dim,
        chunk_count=coll.chunk_count,
        document_count=coll.document_count,
        updated_at=coll.updated_at,
        description=coll.description,
        language=coll.language,
        embedding_model=coll.embedding_model,
        created_at=coll.created_at,
        config=coll.config,
    )


@router.patch(
    "/{collection_id}/embedder-profile",
    response_model=RagCollectionDetailResponse,
)
async def set_embedder_profile(
    collection_id: str,
    body: RagCollectionEmbedderProfileUpdate,
) -> RagCollectionDetailResponse:
    """Attach (or detach) an embedder profile.

    Returns the updated collection on success. 404 if the collection does
    not exist, 409 ``RAG_DIM_MISMATCH`` when the new profile would change
    the vector dimensionality of an already-populated collection, 400
    ``UNKNOWN_EMBEDDER_PROFILE`` for an unregistered alias.
    """
    svc = await _get_service()
    try:
        updated = await svc.set_embedder_profile(
            collection_id=collection_id,
            embedder_profile_id=body.embedder_profile_id,
        )
    except UnknownEmbedderProfile as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": exc.error_code,
                "message": str(exc),
            },
        ) from exc
    except DimensionMismatch as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": exc.error_code,
                "message": str(exc),
            },
        ) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    return RagCollectionDetailResponse(
        id=updated.id,
        name=updated.name,
        tenant_id=updated.tenant_id,
        embedder_profile_id=updated.embedder_profile_id,
        embedding_dim=updated.embedding_dim,
        chunk_count=updated.chunk_count,
        document_count=updated.document_count,
        updated_at=updated.updated_at,
        description=updated.description,
        language=updated.language,
        embedding_model=updated.embedding_model,
        created_at=updated.created_at,
        config=updated.config,
    )
