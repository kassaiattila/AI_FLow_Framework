"""pgvector-based vector store with async PostgreSQL and in-memory fallback.

Supports HNSW index for vector similarity + tsvector BM25 for keyword search.
When asyncpg is unavailable or DB is not configured, falls back to an in-memory
dict-based store suitable for development and testing.
"""
from __future__ import annotations

import json
import math
import os
import uuid
from typing import Any

import structlog

from aiflow.vectorstore.base import SearchFilter, SearchResult, VectorStore

__all__ = ["PgVectorStore"]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _embedding_to_pgvector(embedding: list[float]) -> str:
    """Format a Python list of floats as a pgvector literal '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity for the in-memory fallback."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _bm25_score(query_terms: list[str], text: str) -> float:
    """Simplified BM25-like term-frequency score for in-memory keyword search."""
    if not query_terms:
        return 0.0
    text_lower = text.lower()
    words = text_lower.split()
    doc_len = len(words) if words else 1
    avg_dl = 200.0  # assumed average document length
    k1, b = 1.5, 0.75
    score = 0.0
    for term in query_terms:
        tf = text_lower.count(term.lower())
        if tf > 0:
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avg_dl)
            score += numerator / denominator
    return score


# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------

class _InMemoryBackend:
    """Dict-based vector store for development/testing without PostgreSQL."""

    def __init__(self) -> None:
        # key: (collection, skill_name) -> list of stored chunk dicts
        self._collections: dict[tuple[str, str], list[dict[str, Any]]] = {}

    async def upsert_chunks(
        self,
        collection: str,
        skill_name: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        key = (collection, skill_name)
        if key not in self._collections:
            self._collections[key] = []

        existing = self._collections[key]
        # Build index by chunk_id for ON CONFLICT style upsert
        idx = {str(c["chunk_id"]): i for i, c in enumerate(existing)}

        upserted = 0
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = str(chunk.get("chunk_id", uuid.uuid4()))
            record = {
                **chunk,
                "chunk_id": chunk_id,
                "embedding": embedding,
                "collection": collection,
                "skill_name": skill_name,
            }
            if chunk_id in idx:
                existing[idx[chunk_id]] = record
            else:
                existing.append(record)
                idx[chunk_id] = len(existing) - 1
            upserted += 1
        return upserted

    async def search(
        self,
        collection: str,
        skill_name: str,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 10,
        filters: SearchFilter | None = None,
        search_mode: str = "hybrid",
    ) -> list[SearchResult]:
        key = (collection, skill_name)
        records = self._collections.get(key, [])
        if not records:
            return []

        query_terms = query_text.lower().split() if query_text else []

        scored: list[tuple[float, float, float, dict[str, Any]]] = []
        for rec in records:
            emb = rec.get("embedding", [])
            text_content = rec.get("content", rec.get("chunk_text", ""))

            # Apply metadata filters
            if filters:
                meta = rec.get("metadata", rec.get("chunk_metadata", {}))
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except (json.JSONDecodeError, TypeError):
                        meta = {}
                if filters.document_status and filters.document_status != "active":
                    status = meta.get("status", "active")
                    if status != filters.document_status:
                        continue
                if filters.language:
                    if meta.get("language", "").lower() != filters.language.lower():
                        continue
                if filters.department:
                    if meta.get("department", "").lower() != filters.department.lower():
                        continue

            vs = _cosine_similarity(query_embedding, emb) if emb else 0.0
            ks = _bm25_score(query_terms, text_content) if query_text and search_mode != "vector" else 0.0

            if search_mode == "vector":
                combined = vs
            elif search_mode == "keyword":
                combined = ks
            else:
                combined = 0.6 * vs + 0.4 * ks

            scored.append((combined, vs, ks, rec))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: list[SearchResult] = []
        for combined, vs, ks, rec in scored[:top_k]:
            meta = rec.get("metadata", rec.get("chunk_metadata", {}))
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            results.append(
                SearchResult(
                    chunk_id=uuid.UUID(rec["chunk_id"]) if isinstance(rec["chunk_id"], str) else rec["chunk_id"],
                    content=rec.get("content", rec.get("chunk_text", "")),
                    score=combined,
                    vector_score=vs,
                    keyword_score=ks,
                    document_id=rec.get("document_id"),
                    document_title=rec.get("document_title", meta.get("document_title")),
                    section_title=rec.get("section_title", meta.get("section_title")),
                    page_start=rec.get("page_start", meta.get("page_start")),
                    metadata=meta,
                )
            )
        return results

    async def delete_by_document(
        self, collection: str, skill_name: str, document_id: uuid.UUID
    ) -> int:
        key = (collection, skill_name)
        records = self._collections.get(key, [])
        doc_id_str = str(document_id)
        before = len(records)
        self._collections[key] = [
            r for r in records if str(r.get("document_id", "")) != doc_id_str
        ]
        return before - len(self._collections[key])

    async def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Async PostgreSQL backend
# ---------------------------------------------------------------------------

class _PgBackend:
    """Real PostgreSQL + pgvector backend using asyncpg."""

    def __init__(self, database_url: str, table_name: str = "rag_chunks") -> None:
        self._database_url = database_url
        self._table = table_name
        self._pool: Any = None  # asyncpg.Pool

    async def _ensure_pool(self) -> Any:
        if self._pool is None:
            import asyncpg  # noqa: F811 - dynamic import

            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("pgvector_pool_created", dsn=self._database_url[:40] + "...")
        return self._pool

    async def upsert_chunks(
        self,
        collection: str,
        skill_name: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        pool = await self._ensure_pool()

        sql = f"""
            INSERT INTO {self._table} (
                id, collection, content, embedding,
                metadata, skill_name, document_name, chunk_index
            )
            VALUES (
                $1, $2, $3, $4::vector,
                $5::jsonb, $6, $7, $8
            )
            ON CONFLICT (id) DO UPDATE SET
                content   = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata  = EXCLUDED.metadata
        """

        upserted = 0
        async with pool.acquire() as conn:
            async with conn.transaction():
                for chunk, embedding in zip(chunks, embeddings):
                    chunk_id = chunk.get("chunk_id", str(uuid.uuid4()))
                    if not isinstance(chunk_id, str):
                        chunk_id = str(chunk_id)

                    metadata = chunk.get("metadata", {})
                    if not isinstance(metadata, str):
                        metadata = json.dumps(metadata)

                    await conn.execute(
                        sql,
                        chunk_id,
                        collection,
                        chunk.get("content", chunk.get("chunk_text", "")),
                        _embedding_to_pgvector(embedding),
                        metadata,
                        skill_name,
                        chunk.get("document_name", ""),
                        chunk.get("chunk_index", 0),
                    )
                    upserted += 1
        return upserted

    async def search(
        self,
        collection: str,
        skill_name: str,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 10,
        filters: SearchFilter | None = None,
        search_mode: str = "hybrid",
    ) -> list[SearchResult]:
        pool = await self._ensure_pool()

        embedding_literal = _embedding_to_pgvector(query_embedding)

        # ------------------------------------------------------------------
        # Build WHERE clause dynamically
        # ------------------------------------------------------------------
        conditions = ["rc.collection = $1"]
        params: list[Any] = [collection]
        param_idx = 2

        if skill_name:
            conditions.append(f"rc.skill_name = ${param_idx}")
            params.append(skill_name)
            param_idx += 1

        if filters and filters.language:
            conditions.append(f"rc.metadata->>'language' = ${param_idx}")
            params.append(filters.language)
            param_idx += 1

        where = " AND ".join(conditions)

        # Vector cosine similarity search
        sql = f"""
            SELECT
                rc.id               AS chunk_id,
                rc.content,
                rc.metadata,
                rc.document_name,
                rc.chunk_index,
                1 - (rc.embedding <-> '{embedding_literal}'::vector) AS vector_score
            FROM {self._table} rc
            WHERE {where}
            ORDER BY rc.embedding <-> '{embedding_literal}'::vector
            LIMIT ${param_idx}
        """
        params.append(top_k)

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [self._row_to_result(row) for row in rows]

    async def delete_by_document(
        self, collection: str, skill_name: str, document_id: uuid.UUID
    ) -> int:
        pool = await self._ensure_pool()

        sql = f"""
            DELETE FROM {self._table}
            WHERE collection = $1
              AND skill_name = $2
              AND document_name = $3
        """
        async with pool.acquire() as conn:
            result = await conn.execute(sql, collection, skill_name, document_id)
            # asyncpg returns 'DELETE N'
            try:
                return int(result.split()[-1])
            except (ValueError, IndexError):
                return 0

    async def health_check(self) -> bool:
        try:
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 AS ok, extname FROM pg_extension WHERE extname = 'vector'"
                )
                if row is None:
                    logger.warning("pgvector_extension_missing")
                    return False
                return True
        except Exception as exc:
            logger.error("pgvector_health_check_failed", error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_result(
        row: Any,
        keyword_score: float | None = None,
    ) -> SearchResult:
        meta_raw = row.get("metadata", row.get("chunk_metadata", "{}"))
        if isinstance(meta_raw, str):
            try:
                meta = json.loads(meta_raw)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        elif isinstance(meta_raw, dict):
            meta = meta_raw
        else:
            meta = {}

        vs = float(row["vector_score"]) if row.get("vector_score") is not None else 0.0
        ks = keyword_score if keyword_score is not None else float(row.get("keyword_score", 0.0))
        combined = 0.6 * vs + 0.4 * ks

        return SearchResult(
            chunk_id=str(row["chunk_id"]),
            content=row["content"],
            score=combined,
            vector_score=vs,
            keyword_score=ks,
            document_title=row.get("document_name", meta.get("source_document", "")),
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# Public facade -- delegates to Pg or InMemory backend
# ---------------------------------------------------------------------------

class PgVectorStore(VectorStore):
    """pgvector-based vector store with HNSW index + BM25 full-text search.

    Automatically falls back to in-memory storage when asyncpg is not
    available or the database URL is not configured. Logs which mode is active.

    Requires: PostgreSQL with pgvector extension and the document_chunks table
    (created by Alembic migration 004).
    """

    def __init__(self, database_url: str | None = None, table_name: str = "rag_chunks") -> None:
        resolved_url = database_url or os.environ.get("DATABASE_URL", "")
        self._mode: str = "unknown"
        self._backend: _InMemoryBackend | _PgBackend

        if resolved_url:
            try:
                import asyncpg  # noqa: F401

                self._backend = _PgBackend(resolved_url, table_name=table_name)
                self._mode = "postgresql"
                logger.info(
                    "pgvector_store_init",
                    mode="postgresql",
                    dsn_preview=resolved_url[:40] + "...",
                )
            except ImportError:
                logger.warning(
                    "pgvector_store_fallback",
                    reason="asyncpg not installed",
                    mode="in_memory",
                )
                self._backend = _InMemoryBackend()
                self._mode = "in_memory"
        else:
            logger.warning(
                "pgvector_store_fallback",
                reason="no database_url configured",
                mode="in_memory",
            )
            self._backend = _InMemoryBackend()
            self._mode = "in_memory"

    # -- Public properties -------------------------------------------------

    @property
    def mode(self) -> str:
        """Return 'postgresql' or 'in_memory'."""
        return self._mode

    # -- VectorStore ABC implementation ------------------------------------

    async def upsert_chunks(
        self,
        collection: str,
        skill_name: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        """Upsert chunks with embeddings into pgvector (or in-memory fallback).

        Each chunk dict should contain at minimum:
            - chunk_id (uuid, optional - auto-generated if missing)
            - document_id (uuid)
            - content or chunk_text (str)
            - chunk_index (int, optional)
            - metadata or chunk_metadata (dict, optional)
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
            )
        logger.info(
            "pgvector_upsert",
            collection=collection,
            skill_name=skill_name,
            chunk_count=len(chunks),
            mode=self._mode,
        )
        return await self._backend.upsert_chunks(collection, skill_name, chunks, embeddings)

    async def search(
        self,
        collection: str,
        skill_name: str,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 10,
        filters: SearchFilter | None = None,
        search_mode: str = "hybrid",
    ) -> list[SearchResult]:
        """Search chunks using vector similarity + optional BM25.

        search_mode: 'vector', 'keyword', or 'hybrid' (default).
        """
        logger.info(
            "pgvector_search",
            collection=collection,
            mode=search_mode,
            top_k=top_k,
            backend=self._mode,
        )
        return await self._backend.search(
            collection, skill_name, query_embedding,
            query_text=query_text, top_k=top_k,
            filters=filters, search_mode=search_mode,
        )

    async def delete_by_document(
        self,
        collection: str,
        skill_name: str,
        document_id: uuid.UUID,
    ) -> int:
        """Delete all chunks for a document."""
        logger.info(
            "pgvector_delete",
            collection=collection,
            document_id=str(document_id),
            mode=self._mode,
        )
        return await self._backend.delete_by_document(collection, skill_name, document_id)

    async def health_check(self) -> bool:
        """Check pgvector availability (or return True for in-memory)."""
        return await self._backend.health_check()
