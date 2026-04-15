"""Unit tests for ProviderRegistry + ABC contract tests.

Session: S47 (D0.4) — ProviderRegistry + 4 ABC
"""

from __future__ import annotations

from typing import Any

import pytest

from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.providers.interfaces import (
    ClassifierProvider,
    EmbedderProvider,
    ExtractorProvider,
    ParserProvider,
)
from aiflow.providers.metadata import ProviderMetadata
from aiflow.providers.registry import ProviderRegistry

# ---------------------------------------------------------------------------
# Dummy concrete providers for testing
# ---------------------------------------------------------------------------

_DUMMY_META = ProviderMetadata(
    name="dummy",
    version="0.1.0",
    supported_types=["pdf"],
    speed_class="fast",
    cost_class="free",
    license="MIT",
)


class _DummyParserProvider(ParserProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _DUMMY_META

    async def parse(self, file: IntakeFile, package_context: IntakePackage) -> Any:
        return {"parsed": True}

    async def health_check(self) -> bool:
        return True

    async def estimate_cost(self, file: IntakeFile) -> float:
        return 0.0


class _DummyClassifierProvider(ClassifierProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _DUMMY_META

    async def classify(
        self,
        file: IntakeFile,
        parser_result: Any,
        candidate_classes: list[str],
    ) -> Any:
        return {"class": candidate_classes[0] if candidate_classes else "unknown"}

    async def health_check(self) -> bool:
        return True


class _DummyExtractorProvider(ExtractorProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _DUMMY_META

    async def extract(
        self,
        file: IntakeFile,
        parser_result: Any,
        config: dict[str, Any],
    ) -> Any:
        return {"fields": {}}

    async def health_check(self) -> bool:
        return True


class _DummyEmbedderProvider(EmbedderProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _DUMMY_META

    @property
    def dimensions(self) -> int:
        return 768

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 768 for _ in texts]

    async def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_intake_file() -> IntakeFile:
    return IntakeFile(
        file_path="/tmp/test.pdf",
        file_name="test.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="a" * 64,
    )


def _make_intake_package() -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="test_tenant",
        files=[_make_intake_file()],
    )


# ---------------------------------------------------------------------------
# Registry: register / get / list — all 4 types
# ---------------------------------------------------------------------------


class TestRegistryParser:
    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        reg.register_parser("docling", _DummyParserProvider)
        assert reg.get_parser("docling") is _DummyParserProvider

    def test_list_parsers(self) -> None:
        reg = ProviderRegistry()
        reg.register_parser("a", _DummyParserProvider)
        reg.register_parser("b", _DummyParserProvider)
        assert sorted(reg.list_parsers()) == ["a", "b"]

    def test_get_unregistered_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get_parser("nonexistent")

    def test_register_non_subclass_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(TypeError, match="subclass of ParserProvider"):
            reg.register_parser("bad", str)  # type: ignore[arg-type]


class TestRegistryClassifier:
    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        reg.register_classifier("hybrid", _DummyClassifierProvider)
        assert reg.get_classifier("hybrid") is _DummyClassifierProvider

    def test_list_classifiers(self) -> None:
        reg = ProviderRegistry()
        reg.register_classifier("c1", _DummyClassifierProvider)
        assert reg.list_classifiers() == ["c1"]

    def test_get_unregistered_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get_classifier("nonexistent")

    def test_register_non_subclass_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(TypeError, match="subclass of ClassifierProvider"):
            reg.register_classifier("bad", int)  # type: ignore[arg-type]


class TestRegistryExtractor:
    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        reg.register_extractor("llm", _DummyExtractorProvider)
        assert reg.get_extractor("llm") is _DummyExtractorProvider

    def test_list_extractors(self) -> None:
        reg = ProviderRegistry()
        reg.register_extractor("e1", _DummyExtractorProvider)
        reg.register_extractor("e2", _DummyExtractorProvider)
        assert sorted(reg.list_extractors()) == ["e1", "e2"]

    def test_get_unregistered_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get_extractor("nonexistent")

    def test_register_non_subclass_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(TypeError, match="subclass of ExtractorProvider"):
            reg.register_extractor("bad", dict)  # type: ignore[arg-type]


class TestRegistryEmbedder:
    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        reg.register_embedder("bge", _DummyEmbedderProvider)
        assert reg.get_embedder("bge") is _DummyEmbedderProvider

    def test_list_embedders(self) -> None:
        reg = ProviderRegistry()
        assert reg.list_embedders() == []
        reg.register_embedder("bge", _DummyEmbedderProvider)
        assert reg.list_embedders() == ["bge"]

    def test_get_unregistered_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get_embedder("nonexistent")

    def test_register_non_subclass_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(TypeError, match="subclass of EmbedderProvider"):
            reg.register_embedder("bad", list)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ABC contract tests — verify dummy providers fulfill the contract
# ---------------------------------------------------------------------------


class TestParserContract:
    @pytest.mark.asyncio
    async def test_parse_returns_result(self) -> None:
        provider = _DummyParserProvider()
        result = await provider.parse(_make_intake_file(), _make_intake_package())
        assert result == {"parsed": True}

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        provider = _DummyParserProvider()
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_estimate_cost(self) -> None:
        provider = _DummyParserProvider()
        cost = await provider.estimate_cost(_make_intake_file())
        assert cost == pytest.approx(0.0)

    def test_metadata(self) -> None:
        provider = _DummyParserProvider()
        assert provider.metadata.name == "dummy"
        assert provider.metadata.speed_class == "fast"


class TestEmbedderContract:
    @pytest.mark.asyncio
    async def test_embed_returns_vectors(self) -> None:
        provider = _DummyEmbedderProvider()
        vectors = await provider.embed(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 768

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        provider = _DummyEmbedderProvider()
        assert await provider.health_check() is True

    def test_dimensions(self) -> None:
        provider = _DummyEmbedderProvider()
        assert provider.dimensions == 768

    def test_metadata(self) -> None:
        provider = _DummyEmbedderProvider()
        assert isinstance(provider.metadata, ProviderMetadata)
