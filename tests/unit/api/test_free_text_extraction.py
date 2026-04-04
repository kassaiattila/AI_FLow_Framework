"""
@test_registry:
    suite: api-unit
    component: api.documents.extract_free
    covers: [src/aiflow/services/document_extractor/free_text.py, src/aiflow/api/v1/documents.py]
    phase: S11
    priority: high
    estimated_duration_ms: 500
    requires_services: []
    tags: [free-text, extraction, api]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiflow.services.document_extractor.free_text import (
    FreeTextExtractionResponse,
    FreeTextExtractorConfig,
    FreeTextExtractorService,
    FreeTextQuery,
    FreeTextResult,
)


@pytest.fixture
def mock_session_factory():
    """Create a mock async session factory."""
    factory = AsyncMock()
    session = AsyncMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory, session


class TestFreeTextExtractorService:
    """Tests for the FreeTextExtractorService."""

    def test_config_defaults(self):
        """Config has sensible defaults."""
        config = FreeTextExtractorConfig()
        assert config.default_model == "openai/gpt-4o-mini"
        assert config.max_queries == 20
        assert config.max_document_chars == 30000

    def test_service_name(self, mock_session_factory):
        """Service has correct name and description."""
        factory, _ = mock_session_factory
        svc = FreeTextExtractorService(factory)
        assert svc.service_name == "free_text_extractor"
        desc = svc.service_description.lower()
        assert "free-text" in desc or "free" in desc

    def test_query_model(self):
        """FreeTextQuery model works correctly."""
        q = FreeTextQuery(query="What is the total?", hint="look at totals section")
        assert q.query == "What is the total?"
        assert q.hint == "look at totals section"

    def test_query_model_no_hint(self):
        """FreeTextQuery works without hint."""
        q = FreeTextQuery(query="Who is the vendor?")
        assert q.hint == ""

    def test_result_model(self):
        """FreeTextResult model serializes correctly."""
        r = FreeTextResult(
            query="What is the total?",
            answer="1000 HUF",
            confidence=0.95,
            source_span="Gross total: 1000 HUF",
        )
        d = r.model_dump()
        assert d["query"] == "What is the total?"
        assert d["answer"] == "1000 HUF"
        assert d["confidence"] == 0.95
        assert "1000" in d["source_span"]

    def test_response_model(self):
        """FreeTextExtractionResponse has source=backend."""
        resp = FreeTextExtractionResponse(
            document_id="test-123",
            results=[],
            extraction_time_ms=100.0,
            model_used="openai/gpt-4o-mini",
        )
        assert resp.source == "backend"
        assert resp.document_id == "test-123"

    @pytest.mark.asyncio
    async def test_extract_truncates_queries(self, mock_session_factory):
        """Queries exceeding max_queries are truncated."""
        factory, session = mock_session_factory
        config = FreeTextExtractorConfig(max_queries=3)
        svc = FreeTextExtractorService(factory, config)

        queries = [FreeTextQuery(query=f"Q{i}") for i in range(10)]

        # Mock _load_document_text to return None (doc not found)
        with (
            patch.object(svc, "_load_document_text", new_callable=AsyncMock, return_value=None),
            patch.object(svc, "_log_extraction", new_callable=AsyncMock),
        ):
            result = await svc.extract("doc-1", queries)

        # Should have 3 results (truncated to max_queries)
        assert len(result.results) == 3

    @pytest.mark.asyncio
    async def test_extract_document_not_found(self, mock_session_factory):
        """Returns 'Document not found' when document doesn't exist."""
        factory, session = mock_session_factory
        svc = FreeTextExtractorService(factory)

        with (
            patch.object(svc, "_load_document_text", new_callable=AsyncMock, return_value=None),
            patch.object(svc, "_log_extraction", new_callable=AsyncMock),
        ):
            result = await svc.extract(
                "nonexistent-id",
                [FreeTextQuery(query="What is the total?")],
            )

        assert len(result.results) == 1
        assert result.results[0].answer == "Document not found"
        assert result.results[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_extract_from_text_no_db(self, mock_session_factory):
        """extract_from_text works without DB lookup."""
        factory, _ = mock_session_factory
        svc = FreeTextExtractorService(factory)

        mock_results = [
            FreeTextResult(
                query="Who?",
                answer="Acme Corp",
                confidence=0.9,
                source_span="Vendor: Acme Corp",
            ),
        ]
        with patch.object(svc, "_call_llm", new_callable=AsyncMock, return_value=mock_results):
            results = await svc.extract_from_text(
                "Vendor: Acme Corp\nTotal: 1000 HUF",
                [FreeTextQuery(query="Who?")],
            )

        assert len(results) == 1
        assert results[0].answer == "Acme Corp"

    @pytest.mark.asyncio
    async def test_health_check(self, mock_session_factory):
        """Health check returns True."""
        factory, _ = mock_session_factory
        svc = FreeTextExtractorService(factory)
        assert await svc.health_check() is True
