"""RAG Engine API — collection CRUD, document ingestion, query, feedback, stats."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool, get_engine

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class CollectionCreateRequest(BaseModel):
    name: str
    description: str | None = None
    language: str = "hu"
    embedding_model: str | None = None

class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    language: str = "hu"
    embedding_model: str = "openai/text-embedding-3-small"
    document_count: int = 0
    chunk_count: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    source: str = "backend"

class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse]
    total: int
    source: str = "backend"

class IngestResponse(BaseModel):
    collection_id: str
    files_processed: int = 0
    chunks_created: int = 0
    duration_ms: float = 0
    errors: list[str] = Field(default_factory=list)
    source: str = "backend"

class QueryRequest(BaseModel):
    question: str
    role: str = "expert"
    top_k: int = 5

class QueryResponse(BaseModel):
    query_id: str
    question: str
    answer: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    hallucination_score: float | None = None
    response_time_ms: float = 0
    cost_usd: float = 0
    tokens_used: int = 0
    source: str = "backend"

class FeedbackRequest(BaseModel):
    query_id: str | None = None
    thumbs_up: bool = True
    comment: str | None = None

class FeedbackResponse(BaseModel):
    success: bool
    source: str = "backend"

class StatsResponse(BaseModel):
    collection_id: str
    total_queries: int = 0
    avg_response_time_ms: float = 0
    total_cost_usd: float = 0
    feedback_positive: int = 0
    feedback_negative: int = 0
    source: str = "backend"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_service():
    """Create and start RAG Engine service instance."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from aiflow.services.rag_engine import RAGEngineService, RAGEngineConfig

    engine = await get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    service = RAGEngineService(session_factory=session_factory, config=RAGEngineConfig())
    await service.start()
    return service


# ---------------------------------------------------------------------------
# Collection CRUD
# ---------------------------------------------------------------------------

@router.get("/collections", response_model=CollectionListResponse)
async def list_collections():
    """List all RAG collections."""
    svc = await _get_service()
    try:
        collections = await svc.list_collections()
        return CollectionListResponse(
            collections=[
                CollectionResponse(**c.model_dump())
                for c in collections
            ],
            total=len(collections),
            source="backend",
        )
    except Exception as e:
        logger.error("list_collections_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(request: CollectionCreateRequest):
    """Create a new RAG collection."""
    svc = await _get_service()
    try:
        coll = await svc.create_collection(
            name=request.name,
            description=request.description,
            language=request.language,
            embedding_model=request.embedding_model,
        )
        return CollectionResponse(**coll.model_dump())
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Collection '{request.name}' already exists")
        logger.error("create_collection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str):
    """Get a single collection by ID."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(**coll.model_dump())


@router.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: str, request: CollectionUpdateRequest):
    """Update collection name/description."""
    svc = await _get_service()
    coll = await svc.update_collection(
        collection_id, name=request.name, description=request.description,
    )
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(**coll.model_dump())


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(collection_id: str):
    """Delete a collection and all its chunks."""
    svc = await _get_service()
    deleted = await svc.delete_collection(collection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Collection not found")


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

@router.post("/collections/{collection_id}/ingest", response_model=IngestResponse)
async def ingest_documents(
    collection_id: str,
    files: list[UploadFile] = File(...),
    language: str | None = Query(None),
):
    """Upload and ingest documents into a collection."""
    svc = await _get_service()

    # Verify collection exists
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Save uploaded files to temp directory
    saved_paths: list[Path] = []
    upload_dir = Path(tempfile.mkdtemp(prefix="rag_ingest_"))
    try:
        for f in files:
            dest = upload_dir / (f.filename or "unnamed.pdf")
            content = await f.read()
            dest.write_bytes(content)
            saved_paths.append(dest)

        result = await svc.ingest_documents(
            collection_id=collection_id,
            file_paths=saved_paths,
            language=language,
        )
        return IngestResponse(**result.model_dump())
    except Exception as e:
        logger.error("ingest_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_id}/ingest-status")
async def ingest_status(collection_id: str):
    """Get ingestion status (current chunk/doc counts)."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {
        "collection_id": collection_id,
        "document_count": coll.document_count,
        "chunk_count": coll.chunk_count,
        "source": "backend",
    }


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

@router.post("/collections/{collection_id}/query", response_model=QueryResponse)
async def query_collection(collection_id: str, request: QueryRequest):
    """Run a RAG query against a collection."""
    svc = await _get_service()
    try:
        result = await svc.query(
            collection_id=collection_id,
            question=request.question,
            role=request.role,
            top_k=request.top_k,
        )
        return QueryResponse(**result.model_dump())
    except Exception as e:
        logger.error("query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Feedback & Stats
# ---------------------------------------------------------------------------

@router.post("/collections/{collection_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(collection_id: str, request: FeedbackRequest):
    """Submit feedback (thumbs up/down) for a query."""
    svc = await _get_service()
    success = await svc.submit_feedback(
        collection_id=collection_id,
        query_id=request.query_id,
        thumbs_up=request.thumbs_up,
        comment=request.comment,
    )
    return FeedbackResponse(success=success)


@router.get("/collections/{collection_id}/stats", response_model=StatsResponse)
async def collection_stats(collection_id: str):
    """Get statistics for a collection."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    stats = await svc.get_collection_stats(collection_id)
    return StatsResponse(**stats.model_dump())


# ---------------------------------------------------------------------------
# Chunks (admin)
# ---------------------------------------------------------------------------

@router.get("/collections/{collection_id}/chunks")
async def list_chunks(
    collection_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List chunks in a collection (paginated)."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, content, document_name, metadata, created_at
            FROM rag_chunks
            WHERE collection = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            coll.name, limit, offset,
        )
        total_row = await conn.fetchval(
            "SELECT COUNT(*) FROM rag_chunks WHERE collection = $1",
            coll.name,
        )

    return {
        "chunks": [
            {
                "chunk_id": r["id"],
                "content": r["content"][:300],
                "document_name": r["document_name"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
        "total": total_row or 0,
        "source": "backend",
    }


@router.delete("/collections/{collection_id}/chunks/{chunk_id}", status_code=204)
async def delete_chunk(collection_id: str, chunk_id: str):
    """Delete a single chunk from a collection."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted = await conn.execute(
            "DELETE FROM rag_chunks WHERE id = $1",
            chunk_id,
        )
        if "DELETE 0" in deleted:
            raise HTTPException(status_code=404, detail="Chunk not found")
