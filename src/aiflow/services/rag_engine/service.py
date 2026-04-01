"""RAG Engine service — multi-collection document ingestion, hybrid search, and chat.

Generalizes the aszf_rag_chat skill into a reusable service supporting:
- Multi-collection CRUD (create, list, get, update, delete)
- Document ingestion (parse → chunk → embed → store)
- Hybrid RAG query (vector + BM25 + RRF → LLM generation)
- Feedback collection + statistics
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.services.base import BaseService, ServiceConfig

__all__ = ["RAGEngineConfig", "RAGEngineService"]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Config & Models
# ---------------------------------------------------------------------------

class RAGEngineConfig(ServiceConfig):
    """Configuration for the RAG Engine service."""

    default_embedding_model: str = "openai/text-embedding-3-small"
    default_answer_model: str = "openai/gpt-4o"
    default_chunk_size: int = 2000
    default_chunk_overlap: int = 200
    default_top_k: int = 5
    upload_dir: str = "./data/rag"


class CollectionInfo(BaseModel):
    """Collection summary returned by list/get."""

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


class IngestionResult(BaseModel):
    """Result of ingesting documents into a collection."""

    collection_id: str
    files_processed: int = 0
    chunks_created: int = 0
    duration_ms: float = 0
    errors: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Result of a RAG query."""

    query_id: str
    question: str
    answer: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    hallucination_score: float | None = None
    response_time_ms: float = 0
    cost_usd: float = 0
    tokens_used: int = 0


class CollectionStats(BaseModel):
    """Statistics for a collection."""

    collection_id: str
    total_queries: int = 0
    avg_response_time_ms: float = 0
    total_cost_usd: float = 0
    feedback_positive: int = 0
    feedback_negative: int = 0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class RAGEngineService(BaseService):
    """Multi-collection RAG Engine service.

    Reuses existing vectorstore + ingestion modules:
    - PgVectorStore for chunk storage + hybrid search
    - Embedder for text → vector conversion
    - HybridSearchEngine for vector + BM25 + RRF fusion
    - DoclingParser for PDF/DOCX parsing
    - RecursiveChunker for text splitting
    - ModelClient for LLM generation
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: RAGEngineConfig | None = None,
    ) -> None:
        self._ext_config = config or RAGEngineConfig()
        self._session_factory = session_factory
        self._vector_store = None
        self._embedder = None
        self._search_engine = None
        self._model_client = None
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "rag_engine"

    @property
    def service_description(self) -> str:
        return "Multi-collection RAG engine with document ingestion, hybrid search, and chat"

    async def _start(self) -> None:
        """Initialize vector store, embedder, and search engine."""
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://aiflow:aiflow@localhost:5433/aiflow",
        )
        # Convert async URL to sync for PgVectorStore (uses asyncpg directly)
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        try:
            from aiflow.vectorstore.pgvector_store import PgVectorStore
            from aiflow.vectorstore.embedder import Embedder
            from aiflow.vectorstore.search import HybridSearchEngine, SearchConfig
            from aiflow.models.client import ModelClient
            from aiflow.models.litellm_backend import LiteLLMBackend

            backend = LiteLLMBackend()
            self._model_client = ModelClient(
                generation_backend=backend,
                embedding_backend=backend,
            )
            self._vector_store = PgVectorStore(
                database_url=sync_url,
                table_name="rag_chunks",
            )
            self._embedder = Embedder(
                self._model_client,
                default_model=self._ext_config.default_embedding_model,
            )
            search_config = SearchConfig(
                vector_weight=0.6,
                keyword_weight=0.4,
                top_k=self._ext_config.default_top_k,
                search_mode="hybrid",
            )
            self._search_engine = HybridSearchEngine.from_config(
                self._vector_store, search_config
            )
            self._logger.info("rag_engine_modules_initialized")
        except ImportError as e:
            self._logger.warning("rag_engine_modules_partial", error=str(e))

    async def _stop(self) -> None:
        """Clean up resources."""
        self._vector_store = None
        self._embedder = None
        self._search_engine = None

    async def health_check(self) -> bool:
        """Check DB connectivity."""
        try:
            async with self._session_factory() as session:
                r = await session.execute(text("SELECT 1"))
                return r.scalar() == 1
        except Exception:
            return False

    # -----------------------------------------------------------------------
    # Collection CRUD
    # -----------------------------------------------------------------------

    async def create_collection(
        self,
        name: str,
        description: str | None = None,
        language: str = "hu",
        embedding_model: str | None = None,
        config: dict[str, Any] | None = None,
        customer: str = "default",
    ) -> CollectionInfo:
        """Create a new RAG collection."""
        emb_model = embedding_model or self._ext_config.default_embedding_model
        coll_config = config or {}

        import json as _json

        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO rag_collections (name, customer, skill_name, config,
                        description, language, embedding_model)
                    VALUES (:name, :customer, 'rag_engine', CAST(:config AS jsonb),
                        :description, :language, :embedding_model)
                    RETURNING id, created_at, updated_at
                """),
                {
                    "name": name,
                    "customer": customer,
                    "config": _json.dumps(coll_config),
                    "description": description,
                    "language": language,
                    "embedding_model": emb_model,
                },
            )
            row = result.fetchone()
            await session.commit()

        self._logger.info("collection_created", name=name, id=str(row[0]))
        return CollectionInfo(
            id=str(row[0]),
            name=name,
            description=description,
            language=language,
            embedding_model=emb_model,
            config=coll_config,
            created_at=row[1].isoformat() if row[1] else None,
            updated_at=row[2].isoformat() if row[2] else None,
        )

    async def list_collections(self, customer: str = "default") -> list[CollectionInfo]:
        """List all collections."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, description, language, embedding_model,
                           document_count, chunk_count, config, created_at, updated_at
                    FROM rag_collections
                    ORDER BY created_at DESC
                """),
            )
            rows = result.fetchall()

        return [
            CollectionInfo(
                id=str(r[0]),
                name=r[1],
                description=r[2],
                language=r[3] or "hu",
                embedding_model=r[4] or "openai/text-embedding-3-small",
                document_count=r[5] or 0,
                chunk_count=r[6] or 0,
                config=r[7] if isinstance(r[7], dict) else {},
                created_at=r[8].isoformat() if r[8] else None,
                updated_at=r[9].isoformat() if r[9] else None,
            )
            for r in rows
        ]

    async def get_collection(self, collection_id: str) -> CollectionInfo | None:
        """Get a single collection by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, description, language, embedding_model,
                           document_count, chunk_count, config, created_at, updated_at
                    FROM rag_collections WHERE id = :id
                """),
                {"id": collection_id},
            )
            r = result.fetchone()

        if not r:
            return None
        return CollectionInfo(
            id=str(r[0]),
            name=r[1],
            description=r[2],
            language=r[3] or "hu",
            embedding_model=r[4] or "openai/text-embedding-3-small",
            document_count=r[5] or 0,
            chunk_count=r[6] or 0,
            config=r[7] if isinstance(r[7], dict) else {},
            created_at=r[8].isoformat() if r[8] else None,
            updated_at=r[9].isoformat() if r[9] else None,
        )

    async def update_collection(
        self, collection_id: str, name: str | None = None, description: str | None = None
    ) -> CollectionInfo | None:
        """Update collection name/description."""
        updates = []
        params: dict[str, Any] = {"id": collection_id}
        if name is not None:
            updates.append("name = :name")
            params["name"] = name
        if description is not None:
            updates.append("description = :description")
            params["description"] = description
        if not updates:
            return await self.get_collection(collection_id)

        updates.append("updated_at = NOW()")

        async with self._session_factory() as session:
            await session.execute(
                text(f"UPDATE rag_collections SET {', '.join(updates)} WHERE id = :id"),
                params,
            )
            await session.commit()

        return await self.get_collection(collection_id)

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection and its chunks."""
        coll = await self.get_collection(collection_id)
        if not coll:
            return False

        async with self._session_factory() as session:
            # Delete chunks from rag_chunks table
            await session.execute(
                text("DELETE FROM rag_chunks WHERE collection = :name"),
                {"name": coll.name},
            )
            # Delete collection record (cascades to rag_feedback)
            await session.execute(
                text("DELETE FROM rag_collections WHERE id = :id"),
                {"id": collection_id},
            )
            await session.commit()

        self._logger.info("collection_deleted", id=collection_id, name=coll.name)
        return True

    # -----------------------------------------------------------------------
    # Ingestion
    # -----------------------------------------------------------------------

    async def ingest_documents(
        self,
        collection_id: str,
        file_paths: list[str | Path],
        language: str | None = None,
    ) -> IngestionResult:
        """Ingest documents into a collection: parse → chunk → embed → store."""
        import time

        start = time.time()
        coll = await self.get_collection(collection_id)
        if not coll:
            return IngestionResult(
                collection_id=collection_id,
                errors=["Collection not found"],
            )

        errors: list[str] = []
        total_chunks = 0

        try:
            from aiflow.ingestion.parsers.docling_parser import DoclingParser
            from aiflow.ingestion.chunkers.recursive_chunker import RecursiveChunker, ChunkingConfig

            parser = DoclingParser()
            chunker = RecursiveChunker(ChunkingConfig(
                chunk_size=self._ext_config.default_chunk_size,
                chunk_overlap=self._ext_config.default_chunk_overlap,
            ))

            for fp in file_paths:
                try:
                    # Parse
                    doc = parser.parse(fp)
                    doc_text = doc.markdown or doc.text
                    if not doc_text.strip():
                        errors.append(f"{Path(fp).name}: empty document")
                        continue

                    # Chunk
                    chunks = chunker.chunk_text(doc_text, metadata={
                        "document_name": doc.file_name or Path(fp).name,
                        "file_type": doc.file_type,
                        "language": language or coll.language,
                    })

                    if not chunks:
                        errors.append(f"{Path(fp).name}: no chunks generated")
                        continue

                    # Embed
                    chunk_texts = [c.text for c in chunks]
                    embeddings = await self._embedder.embed_texts(chunk_texts)

                    # Store
                    chunk_dicts = [
                        {
                            "id": str(uuid.uuid4()),
                            "content": c.text,
                            "metadata": {
                                **c.metadata,
                                "chunk_index": c.index,
                            },
                            "document_name": c.metadata.get("document_name", Path(fp).name),
                        }
                        for c in chunks
                    ]
                    stored = await self._vector_store.upsert_chunks(
                        collection=coll.name,
                        skill_name="rag_engine",
                        chunks=chunk_dicts,
                        embeddings=embeddings,
                    )
                    total_chunks += stored
                    self._logger.info(
                        "file_ingested",
                        file=Path(fp).name,
                        chunks=stored,
                        collection=coll.name,
                    )
                except Exception as e:
                    errors.append(f"{Path(fp).name}: {e}")
                    self._logger.error("ingest_file_error", file=str(fp), error=str(e))

            # Update collection stats
            async with self._session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE rag_collections
                        SET document_count = document_count + :docs,
                            chunk_count = chunk_count + :chunks,
                            last_ingest_at = NOW(),
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"docs": len(file_paths) - len(errors), "chunks": total_chunks, "id": collection_id},
                )
                await session.commit()

        except ImportError as e:
            errors.append(f"Module not available: {e}")

        elapsed = (time.time() - start) * 1000
        return IngestionResult(
            collection_id=collection_id,
            files_processed=len(file_paths) - len(errors),
            chunks_created=total_chunks,
            duration_ms=elapsed,
            errors=errors,
        )

    # -----------------------------------------------------------------------
    # Query
    # -----------------------------------------------------------------------

    async def query(
        self,
        collection_id: str,
        question: str,
        role: str = "expert",
        top_k: int | None = None,
    ) -> QueryResult:
        """Run a RAG query: embed → search → generate → log."""
        import time

        start = time.time()
        query_id = str(uuid.uuid4())
        k = top_k or self._ext_config.default_top_k

        coll = await self.get_collection(collection_id)
        if not coll:
            return QueryResult(query_id=query_id, question=question, answer="Collection not found.")

        if coll.chunk_count == 0:
            elapsed = (time.time() - start) * 1000
            return QueryResult(
                query_id=query_id, question=question,
                answer="A kollekcio ures. Tolts fel dokumentumokat eloszor.",
                response_time_ms=elapsed,
            )

        if self._embedder is None:
            elapsed = (time.time() - start) * 1000
            logger.error("query_failed_no_embedder", collection_id=collection_id)
            return QueryResult(
                query_id=query_id, question=question,
                answer="Embedder not initialized. Check OPENAI_API_KEY environment variable.",
                response_time_ms=elapsed,
            )

        # Embed query
        query_embedding = await self._embedder.embed_query(question)

        # Hybrid search
        results = await self._search_engine.search(
            collection=coll.name,
            skill_name="rag_engine",
            query_embedding=query_embedding,
            query_text=question,
            top_k=k,
        )

        # Build context from search results
        sources = []
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[{i}] {r.content}")
            sources.append({
                "index": i,
                "content": r.content[:200],
                "score": round(r.score, 3),
                "document_title": r.document_title,
                "section_title": r.section_title,
            })

        context = "\n\n".join(context_parts) if context_parts else "No relevant documents found."

        # Generate answer
        role_instructions = {
            "baseline": "Answer based on the provided context. Be concise.",
            "mentor": "Explain in detail, provide examples, help the user understand deeply.",
            "expert": "Provide precise, authoritative answers with citations [N] to sources.",
        }
        system_prompt = (
            f"You are a knowledgeable assistant. {role_instructions.get(role, role_instructions['expert'])}\n\n"
            f"Context:\n{context}\n\n"
            "If the context doesn't contain the answer, say so. Always cite sources using [N] notation."
        )

        answer = ""
        cost = 0.0
        tokens = 0
        try:
            result = await self._model_client.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                model=self._ext_config.default_answer_model,
                temperature=0.3,
                max_tokens=2048,
            )
            answer = result.output.text if hasattr(result.output, "text") else str(result.output)
            cost = result.cost_usd
            tokens = result.input_tokens + result.output_tokens
        except Exception as e:
            answer = f"Error generating answer: {e}"
            self._logger.error("query_generation_error", error=str(e))

        elapsed = (time.time() - start) * 1000

        # Log query
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text("""
                        INSERT INTO rag_query_log
                            (id, collection, question, answer, sources_count,
                             response_time_ms, cost_usd, role, collection_id)
                        VALUES (:id, :collection, :question, :answer, :sources_count,
                                :response_time_ms, :cost_usd, :role, :collection_id)
                    """),
                    {
                        "id": query_id,
                        "collection": coll.name,
                        "question": question,
                        "answer": answer,
                        "sources_count": len(sources),
                        "response_time_ms": elapsed,
                        "cost_usd": cost,
                        "role": role,
                        "collection_id": collection_id,
                    },
                )
                await session.commit()
        except Exception as e:
            self._logger.warning("query_log_failed", error=str(e))

        return QueryResult(
            query_id=query_id,
            question=question,
            answer=answer,
            sources=sources,
            response_time_ms=elapsed,
            cost_usd=cost,
            tokens_used=tokens,
        )

    # -----------------------------------------------------------------------
    # Feedback & Stats
    # -----------------------------------------------------------------------

    async def submit_feedback(
        self,
        collection_id: str,
        query_id: str | None = None,
        thumbs_up: bool = True,
        comment: str | None = None,
    ) -> bool:
        """Submit feedback for a query."""
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text("""
                        INSERT INTO rag_feedback (query_id, collection_id, thumbs_up, comment)
                        VALUES (:query_id, :collection_id, :thumbs_up, :comment)
                    """),
                    {
                        "query_id": query_id,
                        "collection_id": collection_id,
                        "thumbs_up": thumbs_up,
                        "comment": comment,
                    },
                )
                await session.commit()
            return True
        except Exception as e:
            self._logger.warning("feedback_save_failed", error=str(e))
            return False

    async def get_collection_stats(self, collection_id: str) -> CollectionStats:
        """Get statistics for a collection."""
        async with self._session_factory() as session:
            # Query stats
            qr = await session.execute(
                text("""
                    SELECT COUNT(*), COALESCE(AVG(response_time_ms), 0),
                           COALESCE(SUM(cost_usd), 0)
                    FROM rag_query_log WHERE collection_id = :id
                """),
                {"id": collection_id},
            )
            qrow = qr.fetchone()

            # Feedback stats
            fr = await session.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (WHERE thumbs_up = true),
                        COUNT(*) FILTER (WHERE thumbs_up = false)
                    FROM rag_feedback WHERE collection_id = :id
                """),
                {"id": collection_id},
            )
            frow = fr.fetchone()

        return CollectionStats(
            collection_id=collection_id,
            total_queries=qrow[0] if qrow else 0,
            avg_response_time_ms=float(qrow[1]) if qrow else 0,
            total_cost_usd=float(qrow[2]) if qrow else 0,
            feedback_positive=frow[0] if frow else 0,
            feedback_negative=frow[1] if frow else 0,
        )
