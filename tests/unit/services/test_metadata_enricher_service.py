"""
@test_registry:
    suite: service-unit
    component: services.metadata_enricher
    covers: [src/aiflow/services/metadata_enricher/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, metadata-enricher, nlp, keywords, entities]
"""

from __future__ import annotations

import pytest

from aiflow.services.metadata_enricher.service import (
    EnrichmentConfig,
    MetadataEnricherConfig,
    MetadataEnricherService,
)


@pytest.fixture()
def svc() -> MetadataEnricherService:
    return MetadataEnricherService(config=MetadataEnricherConfig())


class TestMetadataEnricherService:
    @pytest.mark.asyncio
    async def test_enrich_extracts_language(self, svc: MetadataEnricherService) -> None:
        """enrich returns configured language in metadata."""
        text = "Ez egy magyar dokumentum a teszteleshez."
        config = EnrichmentConfig(language="hu")
        result = await svc.enrich(text, config)
        assert result.language == "hu"

    @pytest.mark.asyncio
    async def test_enrich_extracts_keywords(self, svc: MetadataEnricherService) -> None:
        """enrich extracts keywords from document text."""
        text = (
            "Python programming language is widely used. "
            "Python data science and Python machine learning are popular fields. "
            "Programming with Python frameworks enables rapid development."
        )
        config = EnrichmentConfig(language="en")
        result = await svc.enrich(text, config)
        assert len(result.keywords) > 0
        # "python" should be the top keyword
        assert "python" in result.keywords

    @pytest.mark.asyncio
    async def test_enrich_detects_entities(self, svc: MetadataEnricherService) -> None:
        """enrich entity extraction returns list (stub returns empty)."""
        text = "Kovacs Peter es Kiss Anna dolgozik a BestIx Kft-nel."
        result = await svc.enrich(text)
        # Stub returns empty entities list
        assert isinstance(result.entities, list)

    @pytest.mark.asyncio
    async def test_enrich_empty_text(self, svc: MetadataEnricherService) -> None:
        """enrich with empty text returns minimal metadata."""
        result = await svc.enrich("")
        assert result.confidence == 0.0
        assert result.keywords == []
        assert result.title is None

    @pytest.mark.asyncio
    async def test_health_check(self, svc: MetadataEnricherService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
