"""
@test_registry:
    suite: service-unit
    component: services.advanced_parser
    covers: [src/aiflow/services/advanced_parser/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, advanced-parser, document, extraction, fallback]
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aiflow.services.advanced_parser.service import (
    AdvancedParserConfig,
    AdvancedParserService,
    ParserConfig,
)


@pytest.fixture()
def svc() -> AdvancedParserService:
    # Use raw-only fallback chain so unit tests don't load heavy parsers
    return AdvancedParserService(config=AdvancedParserConfig(fallback_chain=["raw"]))


class TestAdvancedParserService:
    @pytest.mark.asyncio
    async def test_parse_text_file(self, svc: AdvancedParserService) -> None:
        """parse a .txt file returns ParsedDocument with content."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("Hello World\n\nThis is a test document.")
            f.flush()
            result = await svc.parse(f.name)

        assert result.text != ""
        assert "Hello" in result.text
        assert result.parser_used in ("docling", "unstructured", "raw")
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_parse_unknown_format(self, svc: AdvancedParserService) -> None:
        """parse with non-existent file returns error metadata."""
        result = await svc.parse("/nonexistent/file.xyz")
        assert result.parser_used in ("none", "raw")
        assert "error" in result.metadata or result.text == ""

    @pytest.mark.asyncio
    async def test_parse_config_override(self, svc: AdvancedParserService) -> None:
        """parse with custom ParserConfig uses specified parser."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("Config test content.")
            f.flush()
            config = ParserConfig(parser="raw")
            result = await svc.parse(f.name, config=config)

        assert result.parser_used == "raw"
        assert "Config test" in result.text
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_parsed_document_fields(self, svc: AdvancedParserService) -> None:
        """ParsedDocument has correct fields populated."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("Field test.\n\nAnother paragraph.")
            f.flush()
            result = await svc.parse(f.name)

        assert isinstance(result.text, str)
        assert isinstance(result.pages, int)
        assert isinstance(result.metadata, dict)
        assert isinstance(result.confidence, float)
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_health_check(self, svc: AdvancedParserService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
