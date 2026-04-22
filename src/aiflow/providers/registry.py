"""ProviderRegistry — central registry for pluggable provider classes.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N6,
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.6-5.10
"""

from __future__ import annotations

import structlog

from aiflow.providers.interfaces import (
    ChunkerProvider,
    ClassifierProvider,
    EmbedderProvider,
    ExtractorProvider,
    ParserProvider,
)

__all__ = [
    "ProviderRegistry",
]

logger = structlog.get_logger(__name__)


class ProviderRegistry:
    """Central registry mapping provider names to their classes.

    Stores *classes*, not instances — instantiation is deferred to the
    pipeline runtime so that each tenant can receive its own config.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, type[ParserProvider]] = {}
        self._classifiers: dict[str, type[ClassifierProvider]] = {}
        self._extractors: dict[str, type[ExtractorProvider]] = {}
        self._embedders: dict[str, type[EmbedderProvider]] = {}
        self._chunkers: dict[str, type[ChunkerProvider]] = {}
        logger.info("provider_registry_initialized")

    # -- Parser ---------------------------------------------------------------

    def register_parser(self, name: str, provider_cls: type[ParserProvider]) -> None:
        if not issubclass(provider_cls, ParserProvider):
            raise TypeError(
                f"provider_cls must be a subclass of ParserProvider, got {provider_cls.__name__}"
            )
        self._parsers[name] = provider_cls
        logger.info("provider_registered", kind="parser", name=name)

    def get_parser(self, name: str) -> type[ParserProvider]:
        try:
            return self._parsers[name]
        except KeyError:
            raise KeyError(
                f"Parser provider '{name}' not registered. Available: {list(self._parsers.keys())}"
            ) from None

    def list_parsers(self) -> list[str]:
        return sorted(self._parsers.keys())

    # -- Classifier -----------------------------------------------------------

    def register_classifier(self, name: str, provider_cls: type[ClassifierProvider]) -> None:
        if not issubclass(provider_cls, ClassifierProvider):
            raise TypeError(
                f"provider_cls must be a subclass of ClassifierProvider, got {provider_cls.__name__}"
            )
        self._classifiers[name] = provider_cls
        logger.info("provider_registered", kind="classifier", name=name)

    def get_classifier(self, name: str) -> type[ClassifierProvider]:
        try:
            return self._classifiers[name]
        except KeyError:
            raise KeyError(
                f"Classifier provider '{name}' not registered. "
                f"Available: {list(self._classifiers.keys())}"
            ) from None

    def list_classifiers(self) -> list[str]:
        return sorted(self._classifiers.keys())

    # -- Extractor ------------------------------------------------------------

    def register_extractor(self, name: str, provider_cls: type[ExtractorProvider]) -> None:
        if not issubclass(provider_cls, ExtractorProvider):
            raise TypeError(
                f"provider_cls must be a subclass of ExtractorProvider, got {provider_cls.__name__}"
            )
        self._extractors[name] = provider_cls
        logger.info("provider_registered", kind="extractor", name=name)

    def get_extractor(self, name: str) -> type[ExtractorProvider]:
        try:
            return self._extractors[name]
        except KeyError:
            raise KeyError(
                f"Extractor provider '{name}' not registered. "
                f"Available: {list(self._extractors.keys())}"
            ) from None

    def list_extractors(self) -> list[str]:
        return sorted(self._extractors.keys())

    # -- Embedder -------------------------------------------------------------

    def register_embedder(self, name: str, provider_cls: type[EmbedderProvider]) -> None:
        if not issubclass(provider_cls, EmbedderProvider):
            raise TypeError(
                f"provider_cls must be a subclass of EmbedderProvider, got {provider_cls.__name__}"
            )
        self._embedders[name] = provider_cls
        logger.info("provider_registered", kind="embedder", name=name)

    def get_embedder(self, name: str) -> type[EmbedderProvider]:
        try:
            return self._embedders[name]
        except KeyError:
            raise KeyError(
                f"Embedder provider '{name}' not registered. "
                f"Available: {list(self._embedders.keys())}"
            ) from None

    def list_embedders(self) -> list[str]:
        return sorted(self._embedders.keys())

    # -- Chunker --------------------------------------------------------------

    def register_chunker(self, name: str, provider_cls: type[ChunkerProvider]) -> None:
        if not issubclass(provider_cls, ChunkerProvider):
            raise TypeError(
                f"provider_cls must be a subclass of ChunkerProvider, got {provider_cls.__name__}"
            )
        self._chunkers[name] = provider_cls
        logger.info("provider_registered", kind="chunker", name=name)

    def get_chunker(self, name: str) -> type[ChunkerProvider]:
        try:
            return self._chunkers[name]
        except KeyError:
            raise KeyError(
                f"Chunker provider '{name}' not registered. "
                f"Available: {list(self._chunkers.keys())}"
            ) from None

    def list_chunkers(self) -> list[str]:
        return sorted(self._chunkers.keys())
