"""Vector ops service — vector index lifecycle and collection health management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "IndexConfig",
    "CollectionHealth",
    "VectorOpsConfig",
    "VectorOpsService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class IndexConfig(BaseModel):
    """Configuration for index optimization."""

    algorithm: str = "hnsw"
    m: int = 32
    ef_construction: int = 200
    ef_search: int = 100


class CollectionHealth(BaseModel):
    """Health status of a vector collection."""

    total_vectors: int = 0
    index_type: str = "none"
    index_params: dict[str, Any] = Field(default_factory=dict)
    fragmentation_pct: float = 0.0


class VectorOpsConfig(ServiceConfig):
    """Service-level configuration."""

    default_algorithm: str = "hnsw"
    default_m: int = 32
    default_ef_construction: int = 200


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class VectorOpsService(BaseService):
    """Vector index lifecycle management for pgvector collections.

    Provides:
    - Collection health monitoring (vector count, index type, fragmentation)
    - Index optimization (HNSW parameter tuning)
    - Bulk delete with filter conditions
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        config: VectorOpsConfig | None = None,
    ) -> None:
        self._ext_config = config or VectorOpsConfig()
        self._session_factory = session_factory
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "vector_ops"

    @property
    def service_description(self) -> str:
        return "Vector index lifecycle and collection health management"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        if self._session_factory is None:
            return True
        try:
            from sqlalchemy import text

            async with self._session_factory() as session:
                r = await session.execute(text("SELECT 1"))
                return r.scalar() == 1
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Collection health
    # ------------------------------------------------------------------

    async def get_collection_health(self, collection_id: str) -> CollectionHealth:
        """Query pgvector stats for a collection.

        Args:
            collection_id: Collection identifier (maps to table/partition).

        Returns:
            CollectionHealth with vector count, index info, fragmentation.
        """
        if self._session_factory is None:
            self._logger.warning("no_session_factory", note="Returning default health")
            return CollectionHealth()

        from sqlalchemy import text

        try:
            async with self._session_factory() as session:
                # Count vectors in collection
                count_result = await session.execute(
                    text("SELECT COUNT(*) FROM vector_chunks WHERE collection_id = :cid"),
                    {"cid": collection_id},
                )
                total = count_result.scalar() or 0

                # Check for HNSW index on the table
                idx_result = await session.execute(
                    text(
                        "SELECT indexdef FROM pg_indexes "
                        "WHERE tablename = 'vector_chunks' "
                        "AND indexdef LIKE '%hnsw%' "
                        "LIMIT 1"
                    )
                )
                idx_row = idx_result.fetchone()
                index_type = "hnsw" if idx_row else "none"

                # Estimate fragmentation via dead tuple ratio
                frag_result = await session.execute(
                    text(
                        "SELECT n_dead_tup, n_live_tup "
                        "FROM pg_stat_user_tables "
                        "WHERE relname = 'vector_chunks'"
                    )
                )
                frag_row = frag_result.fetchone()
                frag_pct = 0.0
                if frag_row and frag_row[1] and frag_row[1] > 0:
                    frag_pct = round((frag_row[0] / (frag_row[0] + frag_row[1])) * 100, 2)

            self._logger.info(
                "collection_health_checked",
                collection_id=collection_id,
                total_vectors=total,
                index_type=index_type,
                fragmentation_pct=frag_pct,
            )

            return CollectionHealth(
                total_vectors=total,
                index_type=index_type,
                index_params={"algorithm": index_type},
                fragmentation_pct=frag_pct,
            )

        except Exception as exc:
            self._logger.error(
                "collection_health_failed",
                collection_id=collection_id,
                error=str(exc),
            )
            return CollectionHealth()

    # ------------------------------------------------------------------
    # Index optimization
    # ------------------------------------------------------------------

    async def optimize_index(
        self, collection_id: str, config: IndexConfig | None = None
    ) -> dict[str, Any]:
        """Optimize the vector index for a collection.

        Args:
            collection_id: Collection identifier.
            config: Index parameters (algorithm, m, ef_construction, ef_search).

        Returns:
            Dict with optimization result metadata.
        """
        cfg = config or IndexConfig(
            algorithm=self._ext_config.default_algorithm,
            m=self._ext_config.default_m,
            ef_construction=self._ext_config.default_ef_construction,
        )

        if self._session_factory is None:
            self._logger.warning("no_session_factory", note="Cannot optimize index")
            return {
                "status": "skipped",
                "reason": "no_session_factory",
                "collection_id": collection_id,
            }

        from sqlalchemy import text

        try:
            async with self._session_factory() as session:
                # Set HNSW search parameters for the session
                await session.execute(text(f"SET hnsw.ef_search = {cfg.ef_search}"))

                # VACUUM ANALYZE to reduce fragmentation
                # Note: VACUUM cannot run inside a transaction in standard mode,
                # so we log intent and return config for manual execution.
                await session.commit()

            self._logger.info(
                "optimize_index_completed",
                collection_id=collection_id,
                algorithm=cfg.algorithm,
                m=cfg.m,
                ef_construction=cfg.ef_construction,
            )

            return {
                "status": "completed",
                "collection_id": collection_id,
                "config": cfg.model_dump(),
                "note": "HNSW ef_search set; run VACUUM ANALYZE manually for full optimization",
            }

        except Exception as exc:
            self._logger.error(
                "optimize_index_failed",
                collection_id=collection_id,
                error=str(exc),
            )
            return {
                "status": "failed",
                "collection_id": collection_id,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Bulk delete
    # ------------------------------------------------------------------

    async def bulk_delete(self, collection_id: str, filter_cond: dict[str, Any]) -> int:
        """Delete vectors matching filter conditions.

        Args:
            collection_id: Collection identifier.
            filter_cond: Filter dict. Supported keys:
                - document_id: delete by source document
                - older_than: ISO date string, delete older vectors
                - ids: list of chunk IDs to delete

        Returns:
            Number of deleted vectors.
        """
        if self._session_factory is None:
            self._logger.warning("no_session_factory", note="Cannot bulk delete")
            return 0

        from sqlalchemy import text

        conditions = ["collection_id = :cid"]
        params: dict[str, Any] = {"cid": collection_id}

        if "document_id" in filter_cond:
            conditions.append("document_id = :doc_id")
            params["doc_id"] = filter_cond["document_id"]

        if "older_than" in filter_cond:
            conditions.append("created_at < :older_than")
            params["older_than"] = filter_cond["older_than"]

        if "ids" in filter_cond and filter_cond["ids"]:
            # Use ANY for array of IDs
            conditions.append("id = ANY(:ids)")
            params["ids"] = filter_cond["ids"]

        where_clause = " AND ".join(conditions)

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text(f"DELETE FROM vector_chunks WHERE {where_clause}"),  # noqa: S608
                    params,
                )
                await session.commit()
                deleted = result.rowcount or 0

            self._logger.info(
                "bulk_delete_completed",
                collection_id=collection_id,
                deleted=deleted,
                filter=filter_cond,
            )
            return deleted

        except Exception as exc:
            self._logger.error(
                "bulk_delete_failed",
                collection_id=collection_id,
                error=str(exc),
            )
            return 0
