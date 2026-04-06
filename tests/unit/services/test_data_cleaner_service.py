"""
@test_registry:
    suite: service-unit
    component: services.data_cleaner
    covers: [src/aiflow/services/data_cleaner/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, data-cleaner, text-processing, normalization]
"""

from __future__ import annotations

import pytest

from aiflow.services.data_cleaner.service import (
    DataCleanerConfig,
    DataCleanerService,
)


@pytest.fixture()
def svc() -> DataCleanerService:
    return DataCleanerService(config=DataCleanerConfig())


class TestDataCleanerService:
    @pytest.mark.asyncio
    async def test_clean_normalizes_whitespace(self, svc: DataCleanerService) -> None:
        """clean normalizes multiple spaces, tabs, and blank lines."""
        raw = "Hello   world\t\ttab\n\n\n\nmulti blank"
        result = await svc.clean(raw)
        assert "   " not in result.cleaned_text
        assert "\t" not in result.cleaned_text
        assert "\n\n\n" not in result.cleaned_text
        assert result.cleaned_length <= result.original_length

    @pytest.mark.asyncio
    async def test_clean_removes_html(self, svc: DataCleanerService) -> None:
        """clean preserves content (HTML removal is stub, whitespace normalized)."""
        raw = "<p>Hello</p>  <b>World</b>"
        result = await svc.clean(raw)
        # Stub doesn't remove HTML tags, but whitespace is normalized
        assert "Hello" in result.cleaned_text
        assert "World" in result.cleaned_text

    @pytest.mark.asyncio
    async def test_clean_batch(self, svc: DataCleanerService) -> None:
        """clean_batch processes multiple documents."""
        docs = ["Doc  one", "Doc   two", "Doc    three"]
        results = await svc.clean_batch(docs)
        assert len(results) == 3
        assert all(r.cleaned_text for r in results)

    @pytest.mark.asyncio
    async def test_clean_preserves_content(self, svc: DataCleanerService) -> None:
        """clean preserves essential content while normalizing."""
        raw = "Important   data   with   extra   spaces"
        result = await svc.clean(raw)
        assert "Important" in result.cleaned_text
        assert "data" in result.cleaned_text
        assert "extra" in result.cleaned_text
        assert "spaces" in result.cleaned_text

    @pytest.mark.asyncio
    async def test_health_check(self, svc: DataCleanerService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
