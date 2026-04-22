"""Abstract provider interfaces — 4 pluggable provider ABCs.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N6,
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.6-5.10
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from aiflow.providers.metadata import ProviderMetadata

if TYPE_CHECKING:
    from aiflow.intake.package import IntakeFile, IntakePackage

__all__ = [
    "ParserProvider",
    "ClassifierProvider",
    "ExtractorProvider",
    "EmbedderProvider",
    "ChunkerProvider",
]

# Result types are forward-referenced as strings — they will be defined
# in later Phase 1a sessions (ExtractionResult, ClassificationResult, etc.).
# For now the ABCs use Any return types to avoid circular imports.

ParserResult = Any
ClassificationResult = Any
ExtractionResult = Any
ChunkResult = Any


class ParserProvider(abc.ABC):
    """Abstract interface for document parsing providers."""

    @property
    @abc.abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Provider capability descriptor."""

    @abc.abstractmethod
    async def parse(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
    ) -> ParserResult:
        """Parse a single file within its package context."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is operational."""

    @abc.abstractmethod
    async def estimate_cost(self, file: IntakeFile) -> float:
        """Estimate processing cost for a file (0.0 = free)."""


class ClassifierProvider(abc.ABC):
    """Abstract interface for document classification providers."""

    @property
    @abc.abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Provider capability descriptor."""

    @abc.abstractmethod
    async def classify(
        self,
        file: IntakeFile,
        parser_result: ParserResult,
        candidate_classes: list[str],
    ) -> ClassificationResult:
        """Classify a parsed file into one of the candidate classes."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is operational."""


class ExtractorProvider(abc.ABC):
    """Abstract interface for field/data extraction providers."""

    @property
    @abc.abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Provider capability descriptor."""

    @abc.abstractmethod
    async def extract(
        self,
        file: IntakeFile,
        parser_result: ParserResult,
        config: dict[str, Any],
    ) -> ExtractionResult:
        """Extract structured data from a parsed file according to config."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is operational."""


class EmbedderProvider(abc.ABC):
    """Abstract interface for text embedding providers."""

    @property
    @abc.abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Provider capability descriptor."""

    @property
    @abc.abstractmethod
    def embedding_dim(self) -> int:
        """Embedding vector dimensionality."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Concrete model identifier (e.g. 'BAAI/bge-m3', 'text-embedding-3-small')."""

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is operational."""


class ChunkerProvider(abc.ABC):
    """Abstract interface for text chunking providers.

    Sits between ParserProvider and EmbedderProvider in the UC2 RAG
    pipeline. Splits a ParserResult into ChunkResult batches that the
    embedder then converts to vectors.
    """

    @property
    @abc.abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Provider capability descriptor."""

    @abc.abstractmethod
    async def chunk(
        self,
        parser_result: ParserResult,
        package_context: IntakePackage,
    ) -> list[ChunkResult]:
        """Split a parser result into chunks within its package context."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is operational."""
