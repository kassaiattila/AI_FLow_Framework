"""AIFlow document management - registry, versioning, freshness enforcement."""

from aiflow.documents.freshness import FreshnessEnforcer, FreshnessReport
from aiflow.documents.registry import (
    Document,
    DocumentRegistry,
    DocumentStatus,
    IngestionStatus,
)
from aiflow.documents.versioning import DocumentVersion, supersede

__all__ = [
    # Registry
    "Document",
    "DocumentRegistry",
    "DocumentStatus",
    "IngestionStatus",
    # Freshness
    "FreshnessEnforcer",
    "FreshnessReport",
    # Versioning
    "DocumentVersion",
    "supersede",
]
