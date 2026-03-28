"""Document versioning - supersede, version chains."""
from __future__ import annotations

import uuid

import structlog
from pydantic import BaseModel

from aiflow.documents.registry import DocumentRegistry, DocumentStatus

__all__ = [
    "DocumentVersion",
    "supersede",
    "get_version_chain",
]

logger = structlog.get_logger(__name__)


class DocumentVersion(BaseModel):
    """Snapshot describing one link in a document's version chain."""

    document_id: uuid.UUID
    version_number: int
    supersedes_id: uuid.UUID | None = None


def supersede(
    registry: DocumentRegistry,
    old_doc_id: uuid.UUID,
    new_doc_id: uuid.UUID,
) -> tuple[DocumentVersion, DocumentVersion]:
    """Atomically mark *old_doc_id* as superseded and link *new_doc_id*.

    Returns a ``(old_version, new_version)`` tuple.
    """
    old_doc = registry.get(old_doc_id)
    new_doc = registry.get(new_doc_id)

    # Mark old as superseded
    registry.update_status(old_doc_id, DocumentStatus.SUPERSEDED)

    # Link new document to old
    new_doc.supersedes_id = old_doc_id
    new_doc.version_number = old_doc.version_number + 1

    logger.info(
        "document.superseded",
        old_doc_id=str(old_doc_id),
        new_doc_id=str(new_doc_id),
        new_version=new_doc.version_number,
    )

    old_version = DocumentVersion(
        document_id=old_doc.id,
        version_number=old_doc.version_number,
        supersedes_id=old_doc.supersedes_id,
    )
    new_version = DocumentVersion(
        document_id=new_doc.id,
        version_number=new_doc.version_number,
        supersedes_id=new_doc.supersedes_id,
    )
    return old_version, new_version


def get_version_chain(
    registry: DocumentRegistry,
    doc_id: uuid.UUID,
) -> list[DocumentVersion]:
    """Walk backwards through ``supersedes_id`` links and return the full chain.

    The returned list is ordered oldest-first (index 0 is the original).
    """
    chain: list[DocumentVersion] = []
    current_id: uuid.UUID | None = doc_id

    visited: set[uuid.UUID] = set()
    while current_id is not None:
        if current_id in visited:
            logger.warning("document.version_chain_cycle", doc_id=str(current_id))
            break
        visited.add(current_id)

        doc = registry.get(current_id)
        chain.append(
            DocumentVersion(
                document_id=doc.id,
                version_number=doc.version_number,
                supersedes_id=doc.supersedes_id,
            )
        )
        current_id = doc.supersedes_id

    chain.reverse()
    return chain
