"""ProviderRegistry contract E2E — registration, lookup, ABC enforcement.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, providers]

Exercises 106_ Section 5.6-5.10: register/get for all 4 provider kinds,
unknown-name errors, ABC subclass enforcement, and contract (every ABC
method is implementable and callable).
"""

from __future__ import annotations

from typing import Any

import pytest

from aiflow.providers.interfaces import (
    ClassifierProvider,
    EmbedderProvider,
    ExtractorProvider,
    ParserProvider,
)
from aiflow.providers.metadata import ProviderMetadata
from aiflow.providers.registry import ProviderRegistry

# ---------------------------------------------------------------------------
# Minimal concrete implementations (ABC contract test harness)
# ---------------------------------------------------------------------------


def _meta(name: str, cost: str = "cheap") -> ProviderMetadata:
    return ProviderMetadata(
        name=name,
        version="1.0.0",
        supported_types=["pdf"],
        speed_class="normal",
        gpu_required=False,
        cost_class=cost,  # type: ignore[arg-type]
        license="MIT",
    )


class StubParser(ParserProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _meta("stub_parser")

    async def parse(self, file: Any, package_context: Any) -> Any:
        return {"text": "parsed", "file": file.file_name}

    async def health_check(self) -> bool:
        return True

    async def estimate_cost(self, file: Any) -> float:
        return 0.01


class StubClassifier(ClassifierProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _meta("stub_classifier")

    async def classify(
        self,
        file: Any,
        parser_result: Any,
        candidate_classes: list[str],
    ) -> Any:
        return {"label": candidate_classes[0] if candidate_classes else "unknown"}

    async def health_check(self) -> bool:
        return True


class StubExtractor(ExtractorProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _meta("stub_extractor")

    async def extract(self, file: Any, parser_result: Any, config: dict[str, Any]) -> Any:
        return {"fields": {"total": 42}}

    async def health_check(self) -> bool:
        return True


class StubEmbedder(EmbedderProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _meta("stub_embedder", cost="free")

    @property
    def dimensions(self) -> int:
        return 1024

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]

    async def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Registration + lookup
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_empty_registry_has_no_providers(self) -> None:
        reg = ProviderRegistry()
        assert reg.list_parsers() == []
        assert reg.list_classifiers() == []
        assert reg.list_extractors() == []
        assert reg.list_embedders() == []

    def test_register_parser(self) -> None:
        reg = ProviderRegistry()
        reg.register_parser("stub", StubParser)
        assert reg.list_parsers() == ["stub"]
        assert reg.get_parser("stub") is StubParser

    def test_register_classifier(self) -> None:
        reg = ProviderRegistry()
        reg.register_classifier("stub", StubClassifier)
        assert reg.get_classifier("stub") is StubClassifier

    def test_register_extractor(self) -> None:
        reg = ProviderRegistry()
        reg.register_extractor("stub", StubExtractor)
        assert reg.get_extractor("stub") is StubExtractor

    def test_register_embedder(self) -> None:
        reg = ProviderRegistry()
        reg.register_embedder("stub", StubEmbedder)
        assert reg.get_embedder("stub") is StubEmbedder

    def test_lookup_unknown_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get_parser("missing")
        with pytest.raises(KeyError, match="not registered"):
            reg.get_classifier("missing")
        with pytest.raises(KeyError, match="not registered"):
            reg.get_extractor("missing")
        with pytest.raises(KeyError, match="not registered"):
            reg.get_embedder("missing")

    def test_list_parsers_sorted(self) -> None:
        reg = ProviderRegistry()

        class StubB(StubParser):
            pass

        reg.register_parser("z_parser", StubParser)
        reg.register_parser("a_parser", StubB)
        assert reg.list_parsers() == ["a_parser", "z_parser"]


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------


class TestAbcEnforcement:
    def test_parser_rejects_non_subclass(self) -> None:
        reg = ProviderRegistry()

        class NotAParser:
            pass

        with pytest.raises(TypeError, match="ParserProvider"):
            reg.register_parser("bad", NotAParser)  # type: ignore[arg-type]

    def test_classifier_rejects_non_subclass(self) -> None:
        reg = ProviderRegistry()

        class NotAClassifier:
            pass

        with pytest.raises(TypeError, match="ClassifierProvider"):
            reg.register_classifier("bad", NotAClassifier)  # type: ignore[arg-type]

    def test_extractor_rejects_non_subclass(self) -> None:
        reg = ProviderRegistry()

        class NotAnExtractor:
            pass

        with pytest.raises(TypeError, match="ExtractorProvider"):
            reg.register_extractor("bad", NotAnExtractor)  # type: ignore[arg-type]

    def test_embedder_rejects_non_subclass(self) -> None:
        reg = ProviderRegistry()

        class NotAnEmbedder:
            pass

        with pytest.raises(TypeError, match="EmbedderProvider"):
            reg.register_embedder("bad", NotAnEmbedder)  # type: ignore[arg-type]

    def test_abc_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            ParserProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ClassifierProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ExtractorProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            EmbedderProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# End-to-end contract (every ABC method callable)
# ---------------------------------------------------------------------------


class TestContractInvocation:
    @pytest.mark.asyncio
    async def test_parser_contract(self) -> None:
        parser = StubParser()
        assert parser.metadata.name == "stub_parser"

        class _Fake:
            file_name = "doc.pdf"

        result = await parser.parse(_Fake(), object())
        assert result["text"] == "parsed"
        assert await parser.health_check() is True
        assert await parser.estimate_cost(_Fake()) == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_classifier_contract(self) -> None:
        classifier = StubClassifier()
        result = await classifier.classify(object(), object(), ["invoice", "receipt"])
        assert result["label"] == "invoice"
        assert await classifier.health_check() is True

    @pytest.mark.asyncio
    async def test_extractor_contract(self) -> None:
        extractor = StubExtractor()
        result = await extractor.extract(object(), object(), {"schema": "v1"})
        assert result["fields"]["total"] == 42
        assert await extractor.health_check() is True

    @pytest.mark.asyncio
    async def test_embedder_contract(self) -> None:
        embedder = StubEmbedder()
        assert embedder.dimensions == 1024
        vectors = await embedder.embed(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 1024
        assert await embedder.health_check() is True


class TestRegisterLookupRoundtrip:
    def test_full_registry_round_trip(self) -> None:
        reg = ProviderRegistry()
        reg.register_parser("p", StubParser)
        reg.register_classifier("c", StubClassifier)
        reg.register_extractor("e", StubExtractor)
        reg.register_embedder("em", StubEmbedder)

        assert reg.get_parser("p") is StubParser
        assert reg.get_classifier("c") is StubClassifier
        assert reg.get_extractor("e") is StubExtractor
        assert reg.get_embedder("em") is StubEmbedder
