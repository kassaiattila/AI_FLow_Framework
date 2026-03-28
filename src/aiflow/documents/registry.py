"""Document registry for lifecycle tracking.

In-memory implementation; Phase 5 will add DB-backed persistence via SQLAlchemy.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "DocumentStatus",
    "IngestionStatus",
    "Document",
    "DocumentRegistry",
]

logger = structlog.get_logger(__name__)


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    ARCHIVED = "archived"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Represents a managed document in the AIFlow system."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    filename: str
    file_type: str
    file_hash_sha256: str
    document_type: str = ""
    department: str = ""
    language: str = "hu"
    status: DocumentStatus = DocumentStatus.DRAFT
    effective_from: date | None = None
    effective_until: date | None = None
    version_number: int = 1
    supersedes_id: uuid.UUID | None = None
    skill_name: str = ""
    collection_name: str = ""
    chunk_count: int = 0
    ingestion_status: IngestionStatus = IngestionStatus.PENDING
    metadata: dict[str, Any] = {}


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class DocumentRegistry:
    """In-memory document registry.

    Tracks document metadata, status, and supports lookup by ID, hash, or
    collection.  Will be backed by PostgreSQL in Phase 5.
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Document] = {}

    # -- mutators ----------------------------------------------------------

    def register(
        self,
        file_path: str | Path,
        metadata: dict[str, Any],
    ) -> Document:
        """Register a new document from a file path and metadata dict.

        The file hash is computed automatically.  ``metadata`` must include at
        least ``title`` and ``filename`` (or they are derived from the path).
        """
        path = Path(file_path)
        file_hash = _compute_file_hash(path)

        defaults: dict[str, Any] = {
            "filename": path.name,
            "file_type": path.suffix.lstrip(".").lower(),
            "file_hash_sha256": file_hash,
        }
        if "title" not in metadata:
            defaults["title"] = path.stem

        merged = {**defaults, **metadata}
        doc = Document(**merged)
        self._store[doc.id] = doc
        logger.info(
            "document.registered",
            doc_id=str(doc.id),
            filename=doc.filename,
            hash=doc.file_hash_sha256[:12],
        )
        return doc

    def update_status(self, doc_id: uuid.UUID, new_status: DocumentStatus) -> Document:
        """Transition a document to *new_status*."""
        doc = self.get(doc_id)
        old_status = doc.status
        doc.status = new_status
        logger.info(
            "document.status_changed",
            doc_id=str(doc_id),
            old=old_status,
            new=new_status,
        )
        return doc

    # -- queries -----------------------------------------------------------

    def get(self, doc_id: uuid.UUID) -> Document:
        """Return document by ID or raise ``KeyError``."""
        try:
            return self._store[doc_id]
        except KeyError:
            raise KeyError(f"Document {doc_id} not found in registry")

    def list_by_collection(self, collection_name: str | None = None) -> list[Document]:
        """Return all documents, optionally filtered by collection."""
        docs = list(self._store.values())
        if collection_name is not None:
            docs = [d for d in docs if d.collection_name == collection_name]
        return docs

    def find_by_hash(self, file_hash_sha256: str) -> Document | None:
        """Return the first document matching the given SHA-256 hash, or ``None``."""
        for doc in self._store.values():
            if doc.file_hash_sha256 == file_hash_sha256:
                return doc
        return None

    # -- housekeeping ------------------------------------------------------

    def clear(self) -> None:
        """Remove all documents (testing helper)."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return f"DocumentRegistry(count={len(self)})"
