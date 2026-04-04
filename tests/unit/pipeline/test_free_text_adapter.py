"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.free_text
    covers: [src/aiflow/pipeline/adapters/free_text_adapter.py]
    phase: S11
    priority: high
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, adapter, free-text]
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiflow.pipeline.adapters.free_text_adapter import (
    FreeTextExtractAdapter,
    FreeTextExtractInput,
    FreeTextExtractOutput,
)


class TestFreeTextExtractAdapter:
    """Tests for the FreeTextExtractAdapter."""

    def test_adapter_attributes(self):
        """Adapter has correct service name and method."""
        adapter = FreeTextExtractAdapter()
        assert adapter.service_name == "document_extractor"
        assert adapter.method_name == "extract_free_text"

    def test_input_schema(self):
        """Input schema validates correctly."""
        inp = FreeTextExtractInput(
            document_id="doc-123",
            queries=[{"query": "What is the total?", "hint": "totals section"}],
        )
        assert inp.document_id == "doc-123"
        assert len(inp.queries) == 1
        assert inp.model is None

    def test_input_schema_with_model(self):
        """Input schema accepts model override."""
        inp = FreeTextExtractInput(
            document_id="doc-456",
            queries=[{"query": "Who?"}],
            model="openai/gpt-4o",
        )
        assert inp.model == "openai/gpt-4o"

    def test_output_schema(self):
        """Output schema has correct defaults."""
        out = FreeTextExtractOutput()
        assert out.document_id == ""
        assert out.results == []
        assert out.extraction_time_ms == 0.0

    def test_output_schema_with_data(self):
        """Output schema serializes results correctly."""
        out = FreeTextExtractOutput(
            document_id="doc-789",
            results=[
                {"query": "Total?", "answer": "1000", "confidence": 0.9, "source_span": "Total: 1000"},
            ],
            extraction_time_ms=150.5,
            model_used="openai/gpt-4o-mini",
        )
        d = out.model_dump()
        assert d["document_id"] == "doc-789"
        assert len(d["results"]) == 1
        assert d["results"][0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_run_calls_service(self):
        """_run delegates to the service correctly."""
        mock_svc = AsyncMock()
        mock_result = MagicMock()
        mock_result.document_id = "doc-1"
        mock_result.results = []
        mock_result.extraction_time_ms = 50.0
        mock_result.model_used = "test-model"
        mock_svc.extract = AsyncMock(return_value=mock_result)

        adapter = FreeTextExtractAdapter(service=mock_svc)

        input_data = FreeTextExtractInput(
            document_id="doc-1",
            queries=[{"query": "test"}],
        )
        ctx = MagicMock()

        result = await adapter._run(input_data, {}, ctx)

        assert result["document_id"] == "doc-1"
        mock_svc.extract.assert_called_once()
