"""
@test_registry:
    suite: service-unit
    component: services.vector_ops
    covers: [src/aiflow/services/vector_ops/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, vector-ops, pgvector, index, collection]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.vector_ops.service import VectorOpsConfig, VectorOpsService


@pytest.fixture()
def mock_session_factory():
    """Mock SQLAlchemy async session factory."""
    session = AsyncMock()
    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory, session


@pytest.fixture()
def svc(mock_session_factory) -> VectorOpsService:
    factory, _session = mock_session_factory
    return VectorOpsService(session_factory=factory, config=VectorOpsConfig())


class TestVectorOpsService:
    @pytest.mark.asyncio
    async def test_get_collection_health(self, svc: VectorOpsService, mock_session_factory) -> None:
        """get_collection_health returns CollectionHealth with vector count."""
        _factory, session = mock_session_factory

        # count_result → scalar
        count_result = MagicMock()
        count_result.scalar.return_value = 1500

        # idx_result → fetchone (HNSW index found)
        idx_result = MagicMock()
        idx_result.fetchone.return_value = ("CREATE INDEX ... hnsw ...",)

        # frag_result → fetchone (dead/live tuples)
        frag_result = MagicMock()
        frag_result.fetchone.return_value = (50, 950)

        session.execute = AsyncMock(side_effect=[count_result, idx_result, frag_result])

        health = await svc.get_collection_health("coll-001")
        assert health.total_vectors == 1500
        assert health.index_type == "hnsw"
        assert health.fragmentation_pct > 0

    @pytest.mark.asyncio
    async def test_optimize_index(self, svc: VectorOpsService, mock_session_factory) -> None:
        """optimize_index sets HNSW params and returns result dict."""
        _factory, session = mock_session_factory
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        result = await svc.optimize_index("coll-001")
        assert result["status"] == "completed"
        assert result["collection_id"] == "coll-001"
        assert "config" in result

    @pytest.mark.asyncio
    async def test_bulk_delete(self, svc: VectorOpsService, mock_session_factory) -> None:
        """bulk_delete returns deleted count."""
        _factory, session = mock_session_factory
        delete_result = MagicMock()
        delete_result.rowcount = 42
        session.execute = AsyncMock(return_value=delete_result)
        session.commit = AsyncMock()

        deleted = await svc.bulk_delete("coll-001", {"document_id": "doc-123"})
        assert deleted == 42

    @pytest.mark.asyncio
    async def test_health_check_no_db(self) -> None:
        """health_check without DB returns True."""
        svc = VectorOpsService(session_factory=None, config=VectorOpsConfig())
        assert await svc.health_check() is True

    @pytest.mark.asyncio
    async def test_service_name(self, svc: VectorOpsService) -> None:
        """service_name is 'vector_ops'."""
        assert svc.service_name == "vector_ops"
