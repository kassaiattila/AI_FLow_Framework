"""Ingestion pipeline - orchestrates parsing, chunking, and registration.

This is the high-level entry point for ingesting a document into the AIFlow
knowledge base.  Phase 3 provides the skeleton; embedding and vector-store
upsert are wired in Phase 4.
"""
from __future__ import annotations

import time
import uuid
from enum import StrEnum
from pathlib import Path

import structlog
from pydantic import BaseModel

from aiflow.documents.registry import (
    DocumentRegistry,
    DocumentStatus,
    IngestionStatus,
)
from aiflow.ingestion.chunkers.semantic_chunker import ChunkingConfig, SemanticChunker

__all__ = [
    "IngestionResultStatus",
    "IngestionResult",
    "IngestionPipeline",
]

logger = structlog.get_logger(__name__)


class IngestionResultStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class IngestionResult(BaseModel):
    """Outcome of an ingestion run."""

    document_id: uuid.UUID
    chunk_count: int = 0
    status: IngestionResultStatus = IngestionResultStatus.SUCCESS
    duration_ms: float = 0.0
    error: str | None = None


class IngestionPipeline:
    """Orchestrate the full document ingestion lifecycle.

    Current capabilities (Phase 3):
    - Register document in the :class:`DocumentRegistry`.
    - Chunk plain-text content with :class:`SemanticChunker`.
    - Track ingestion status transitions.

    Phase 4 additions:
    - Automatic parser dispatch (PDF, DOCX, etc.).
    - Embedding generation and vector-store upsert.
    """

    def __init__(
        self,
        registry: DocumentRegistry,
        chunker: SemanticChunker | None = None,
        chunking_config: ChunkingConfig | None = None,
    ) -> None:
        self._registry = registry
        self._chunker = chunker or SemanticChunker()
        self._chunking_config = chunking_config or ChunkingConfig()

    def run(
        self,
        file_path: str | Path,
        skill_name: str,
        collection_name: str,
        text_content: str | None = None,
    ) -> IngestionResult:
        """Ingest a document.

        Parameters
        ----------
        file_path:
            Path to the source file (used for registration and hashing).
        skill_name:
            The skill this document belongs to.
        collection_name:
            Target vector-store collection.
        text_content:
            Pre-extracted text.  If ``None`` the pipeline reads the file
            as plain text (parser dispatch comes in Phase 4).
        """
        start = time.perf_counter()
        path = Path(file_path)
        doc_id = uuid.uuid4()

        try:
            # Step 1: register
            doc = self._registry.register(
                file_path=path,
                metadata={
                    "id": doc_id,
                    "title": path.stem,
                    "skill_name": skill_name,
                    "collection_name": collection_name,
                    "status": DocumentStatus.DRAFT,
                    "ingestion_status": IngestionStatus.PARSING,
                },
            )

            # Step 2: obtain text
            if text_content is None:
                text_content = path.read_text(encoding="utf-8")

            # Step 3: chunk
            doc.ingestion_status = IngestionStatus.CHUNKING
            chunks = self._chunker.chunk(text_content, self._chunking_config)
            doc.chunk_count = len(chunks)

            # Step 4 (stub): embedding + upsert would go here
            doc.ingestion_status = IngestionStatus.COMPLETED
            self._registry.update_status(doc.id, DocumentStatus.ACTIVE)

            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "ingestion.completed",
                doc_id=str(doc.id),
                chunks=len(chunks),
                duration_ms=round(elapsed_ms, 1),
            )
            return IngestionResult(
                document_id=doc.id,
                chunk_count=len(chunks),
                status=IngestionResultStatus.SUCCESS,
                duration_ms=round(elapsed_ms, 1),
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("ingestion.failed", error=str(exc))
            return IngestionResult(
                document_id=doc_id,
                chunk_count=0,
                status=IngestionResultStatus.FAILED,
                duration_ms=round(elapsed_ms, 1),
                error=str(exc),
            )
