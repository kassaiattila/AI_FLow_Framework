"""Chunker provider implementations.

Exposes the :class:`ChunkerProvider` ABC plus the concrete
``UnstructuredChunker`` (Sprint J S101 — UC2 RAG). The chunker sits
between ParserProvider and EmbedderProvider in the ingest pipeline.
"""

from aiflow.providers.chunker.unstructured import (
    UnstructuredChunker,
    UnstructuredChunkerConfig,
)
from aiflow.providers.interfaces import ChunkerProvider

__all__ = [
    "ChunkerProvider",
    "UnstructuredChunker",
    "UnstructuredChunkerConfig",
]
