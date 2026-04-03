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


class IngestStatusResponse(BaseModel):
    collection_id: str
    document_count: int
    chunk_count: int
    source: str = "backend"


class ChunkItem(BaseModel):
    chunk_id: str
    content: str
    document_name: str | None = None
    created_at: str | None = None


class ChunkListResponse(BaseModel):
    chunks: list[ChunkItem]
    total: int
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


class BulkDeleteCollectionsRequest(BaseModel):
    ids: list[str]


class BulkDeleteCollectionsResponse(BaseModel):
    deleted: int = 0
    source: str = "backend"


@router.post("/collections/delete-bulk", response_model=BulkDeleteCollectionsResponse)
async def delete_collections_bulk(request: BulkDeleteCollectionsRequest):
    """Delete multiple collections by UUID list."""
    svc = await _get_service()
    total = 0
    for cid in request.ids:
        ok = await svc.delete_collection(cid)
        if ok:
            total += 1
    logger.info("collections_bulk_deleted", count=total, ids=request.ids)
    from aiflow.api.audit_helper import audit_log
    await audit_log("bulk_delete", "rag_collection", details={"count": total})
    return BulkDeleteCollectionsResponse(deleted=total)


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

    # Save uploaded files to persistent directory (not temp!)
    saved_paths: list[Path] = []
    project_root = Path(__file__).parent.parent.parent.parent.parent
    upload_dir = project_root / "data" / "uploads" / "rag" / collection_id
    upload_dir.mkdir(parents=True, exist_ok=True)
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


@router.post("/collections/{collection_id}/ingest-stream")
async def ingest_documents_stream(
    collection_id: str,
    files: list[UploadFile] = File(...),
    language: str | None = Query(None),
):
    """Upload and ingest documents with SSE progress streaming.

    Events: step_start, step_done, error, complete.
    Steps: upload, parse, chunk, embed, store.
    """
    import json as _json
    import time as _time
    from fastapi.responses import StreamingResponse

    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    async def event_stream():
        run_start = _time.perf_counter()
        errors: list[str] = []
        total_chunks = 0
        files_ok = 0

        try:
            # Step 0: Upload files to disk
            yield f"data: {_json.dumps({'event': 'step_start', 'step': 0, 'name': 'upload'})}\n\n"
            project_root = Path(__file__).parent.parent.parent.parent.parent
            upload_dir = project_root / "data" / "uploads" / "rag" / collection_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            saved_paths: list[Path] = []
            for f in files:
                dest = upload_dir / (f.filename or "unnamed.pdf")
                content = await f.read()
                dest.write_bytes(content)
                saved_paths.append(dest)
            yield f"data: {_json.dumps({'event': 'step_done', 'step': 0, 'name': 'upload', 'files': len(saved_paths)})}\n\n"

            # Step 1: Parse documents
            yield f"data: {_json.dumps({'event': 'step_start', 'step': 1, 'name': 'parse'})}\n\n"
            from aiflow.ingestion.parsers.docling_parser import DoclingParser
            from aiflow.ingestion.chunkers.recursive_chunker import RecursiveChunker, ChunkingConfig
            parser = DoclingParser()
            parsed_docs = []
            for fp in saved_paths:
                try:
                    doc = parser.parse(fp)
                    doc_text = doc.markdown or doc.text
                    if doc_text.strip():
                        parsed_docs.append((fp, doc, doc_text))
                    else:
                        errors.append(f"{fp.name}: empty document")
                except Exception as e:
                    errors.append(f"{fp.name}: parse error: {e}")
            yield f"data: {_json.dumps({'event': 'step_done', 'step': 1, 'name': 'parse', 'parsed': len(parsed_docs)})}\n\n"

            # Step 2: Chunk
            yield f"data: {_json.dumps({'event': 'step_start', 'step': 2, 'name': 'chunk'})}\n\n"
            chunker = RecursiveChunker(ChunkingConfig(
                chunk_size=svc._ext_config.default_chunk_size,
                chunk_overlap=svc._ext_config.default_chunk_overlap,
            ))
            all_chunks_data: list[tuple[Path, list]] = []
            for fp, doc, doc_text in parsed_docs:
                chunks = chunker.chunk_text(doc_text, metadata={
                    "document_name": doc.file_name or fp.name,
                    "file_type": doc.file_type,
                    "language": language or coll.language,
                })
                if chunks:
                    all_chunks_data.append((fp, chunks))
                else:
                    errors.append(f"{fp.name}: no chunks")
            total_chunk_count = sum(len(c) for _, c in all_chunks_data)
            yield f"data: {_json.dumps({'event': 'step_done', 'step': 2, 'name': 'chunk', 'chunks': total_chunk_count})}\n\n"

            # Step 3: Embed + record cost
            yield f"data: {_json.dumps({'event': 'step_start', 'step': 3, 'name': 'embed'})}\n\n"
            all_embeddings: list[tuple[Path, list, list]] = []
            embed_total_tokens = 0
            for fp, chunks in all_chunks_data:
                chunk_texts = [c.text for c in chunks]
                embeddings = await svc._embedder.embed_texts(chunk_texts)
                all_embeddings.append((fp, chunks, embeddings))
                embed_total_tokens += sum(len(t) // 4 for t in chunk_texts)  # ~4 chars/token estimate

            # Record embedding cost
            try:
                from aiflow.api.cost_recorder import record_cost
                from aiflow.models.cost import ModelCostCalculator
                embed_model = "openai/text-embedding-3-small"
                calc = ModelCostCalculator()
                embed_cost = calc.calculate(embed_model, embed_total_tokens, 0)
                import uuid as _cost_uuid
                await record_cost(
                    workflow_run_id=_cost_uuid.uuid4(),
                    step_name="rag_ingest_embed",
                    model=embed_model,
                    input_tokens=embed_total_tokens,
                    output_tokens=0,
                    cost_usd=embed_cost,
                )
            except Exception:
                pass
            yield f"data: {_json.dumps({'event': 'step_done', 'step': 3, 'name': 'embed', 'tokens': embed_total_tokens})}\n\n"

            # Step 4: Store
            yield f"data: {_json.dumps({'event': 'step_start', 'step': 4, 'name': 'store'})}\n\n"
            import uuid as _uuid
            for fp, chunks, embeddings in all_embeddings:
                chunk_dicts = [
                    {
                        "id": str(_uuid.uuid4()),
                        "content": c.text,
                        "metadata": {**c.metadata, "chunk_index": c.index},
                        "document_name": c.metadata.get("document_name", fp.name),
                    }
                    for c in chunks
                ]
                stored = await svc._vector_store.upsert_chunks(
                    collection=coll.name,
                    skill_name="rag_engine",
                    chunks=chunk_dicts,
                    embeddings=embeddings,
                )
                total_chunks += stored
                files_ok += 1

            # Update collection stats
            from sqlalchemy import text as sa_text
            async with svc._session_factory() as session:
                await session.execute(
                    sa_text("""UPDATE rag_collections
                        SET document_count = document_count + :docs,
                            chunk_count = chunk_count + :chunks,
                            last_ingest_at = NOW(), updated_at = NOW()
                        WHERE id = :id"""),
                    {"docs": files_ok, "chunks": total_chunks, "id": collection_id},
                )
                await session.commit()
            yield f"data: {_json.dumps({'event': 'step_done', 'step': 4, 'name': 'store', 'stored': total_chunks})}\n\n"

            total_ms = int((_time.perf_counter() - run_start) * 1000)
            yield f"data: {_json.dumps({'event': 'complete', 'files_processed': files_ok, 'chunks_created': total_chunks, 'duration_ms': total_ms, 'errors': errors})}\n\n"

        except Exception as e:
            yield f"data: {_json.dumps({'event': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/collections/{collection_id}/ingest-status", response_model=IngestStatusResponse)
async def ingest_status(collection_id: str):
    """Get ingestion status (current chunk/doc counts)."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    return IngestStatusResponse(
        collection_id=collection_id,
        document_count=coll.document_count,
        chunk_count=coll.chunk_count,
        source="backend",
    )


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
        resp = QueryResponse(**result.model_dump())

        # Persist cost to cost_records (best-effort)
        if resp.cost_usd > 0 or resp.tokens_used > 0:
            try:
                from aiflow.api.cost_recorder import record_cost
                await record_cost(
                    workflow_run_id=resp.query_id,
                    step_name="rag_query",
                    model="openai/gpt-4o",
                    input_tokens=resp.tokens_used,
                    output_tokens=0,
                    cost_usd=resp.cost_usd,
                )
            except Exception:
                pass

        return resp
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

@router.get("/collections/{collection_id}/chunks", response_model=ChunkListResponse)
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

    return ChunkListResponse(
        chunks=[
            ChunkItem(
                chunk_id=str(r["id"]),
                content=r["content"][:300],
                document_name=r["document_name"],
                created_at=r["created_at"].isoformat() if r["created_at"] else None,
            )
            for r in rows
        ],
        total=total_row or 0,
        source="backend",
    )


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


# ---------------------------------------------------------------------------
# Collection documents (aggregated from chunks)
# ---------------------------------------------------------------------------

class CollectionDocItem(BaseModel):
    document_name: str
    chunk_count: int
    first_ingested: str | None = None


class CollectionDocsResponse(BaseModel):
    documents: list[CollectionDocItem] = []
    total: int = 0
    source: str = "backend"


@router.get("/collections/{collection_id}/documents", response_model=CollectionDocsResponse)
async def list_collection_documents(collection_id: str):
    """List distinct documents ingested into a collection (aggregated from chunks)."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT document_name, COUNT(*) AS chunk_count, MIN(created_at) AS first_ingested
            FROM rag_chunks
            WHERE collection = $1 AND document_name IS NOT NULL
            GROUP BY document_name
            ORDER BY MIN(created_at) DESC
            """,
            coll.name,
        )

    return CollectionDocsResponse(
        documents=[
            CollectionDocItem(
                document_name=r["document_name"],
                chunk_count=r["chunk_count"],
                first_ingested=r["first_ingested"].isoformat() if r["first_ingested"] else None,
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.delete("/collections/{collection_id}/documents/{doc_name:path}", status_code=204)
async def delete_collection_document(collection_id: str, doc_name: str):
    """Delete all chunks belonging to a specific document in a collection."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM rag_chunks WHERE collection = $1 AND document_name = $2",
            coll.name, doc_name,
        )
        if "DELETE 0" in result:
            raise HTTPException(status_code=404, detail="Document not found in collection")
    logger.info("collection_document_deleted", collection_id=collection_id, document_name=doc_name)
    from aiflow.api.audit_helper import audit_log
    await audit_log("delete", "rag_document", doc_name, {"collection_id": collection_id})


class BulkDeleteDocsRequest(BaseModel):
    document_names: list[str]


class BulkDeleteDocsResponse(BaseModel):
    deleted: int = 0
    chunks_removed: int = 0
    source: str = "backend"


@router.post("/collections/{collection_id}/documents/delete-bulk", response_model=BulkDeleteDocsResponse)
async def delete_collection_documents_bulk(collection_id: str, request: BulkDeleteDocsRequest):
    """Delete multiple documents (and their chunks) from a collection."""
    svc = await _get_service()
    coll = await svc.get_collection(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    pool = await get_pool()
    total_chunks = 0
    async with pool.acquire() as conn:
        for doc_name in request.document_names:
            result = await conn.execute(
                "DELETE FROM rag_chunks WHERE collection = $1 AND document_name = $2",
                coll.name, doc_name,
            )
            count = int(result.split()[-1]) if result else 0
            total_chunks += count

    logger.info("collection_documents_bulk_deleted", collection_id=collection_id, count=len(request.document_names), chunks=total_chunks)
    return BulkDeleteDocsResponse(deleted=len(request.document_names), chunks_removed=total_chunks)
