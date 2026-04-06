"""
@test_registry:
    suite: service-unit
    component: services.rag_engine
    covers: [src/aiflow/services/rag_engine/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, rag-engine, collection, ingestion, search]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.rag_engine.service import RAGEngineConfig, RAGEngineService


def _make_collection_row(
    cid="coll-001",
    name="test-collection",
    desc="Test",
    lang="hu",
    emb="openai/text-embedding-3-small",
    doc_count=5,
    chunk_count=100,
):
    """Mock SQLAlchemy result row for rag_collections."""
    return (
        cid,
        name,
        desc,
        lang,
        emb,
        doc_count,
        chunk_count,
        {},  # config
        None,  # created_at
        None,  # updated_at
    )


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
def svc(mock_session_factory) -> RAGEngineService:
    factory, _session = mock_session_factory
    return RAGEngineService(session_factory=factory, config=RAGEngineConfig())


class TestRAGEngineService:
    @pytest.mark.asyncio
    async def test_list_collections(self, svc: RAGEngineService, mock_session_factory) -> None:
        """list_collections returns CollectionInfo list."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchall.return_value = [
            _make_collection_row("c1", "first"),
            _make_collection_row("c2", "second"),
        ]
        session.execute = AsyncMock(return_value=result)

        collections = await svc.list_collections()
        assert len(collections) == 2
        assert collections[0].id == "c1"
        assert collections[1].name == "second"

    @pytest.mark.asyncio
    async def test_get_collection(self, svc: RAGEngineService, mock_session_factory) -> None:
        """get_collection returns CollectionInfo for existing ID."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchone.return_value = _make_collection_row()
        session.execute = AsyncMock(return_value=result)

        coll = await svc.get_collection("coll-001")
        assert coll is not None
        assert coll.id == "coll-001"
        assert coll.name == "test-collection"

    @pytest.mark.asyncio
    async def test_delete_collection(self, svc: RAGEngineService, mock_session_factory) -> None:
        """delete_collection returns True when collection exists."""
        _factory, session = mock_session_factory

        # get_collection SELECT
        get_result = MagicMock()
        get_result.fetchone.return_value = _make_collection_row()

        # DELETE chunks + DELETE collection
        delete_result = AsyncMock()

        session.execute = AsyncMock(side_effect=[get_result, delete_result, delete_result])
        session.commit = AsyncMock()

        deleted = await svc.delete_collection("coll-001")
        assert deleted is True

    @pytest.mark.asyncio
    async def test_get_collection_stats(self, svc: RAGEngineService, mock_session_factory) -> None:
        """get_collection_stats returns CollectionStats."""
        _factory, session = mock_session_factory

        # query_log aggregation
        qr = MagicMock()
        qr.fetchone.return_value = (25, 150.5, 0.05)

        # feedback aggregation
        fr = MagicMock()
        fr.fetchone.return_value = (20, 5)

        session.execute = AsyncMock(side_effect=[qr, fr])

        stats = await svc.get_collection_stats("coll-001")
        assert stats.collection_id == "coll-001"
        assert stats.total_queries == 25
        assert stats.feedback_positive == 20
        assert stats.feedback_negative == 5

    @pytest.mark.asyncio
    async def test_health_check(self, svc: RAGEngineService, mock_session_factory) -> None:
        """health_check with DB returns True when SELECT 1 succeeds."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=result)

        assert await svc.health_check() is True
