"""Metadata enricher service — auto-extract metadata from documents."""

from aiflow.services.metadata_enricher.service import (
    EnrichedMetadata,
    EnrichmentConfig,
    MetadataEnricherConfig,
    MetadataEnricherService,
)

__all__ = [
    "EnrichedMetadata",
    "EnrichmentConfig",
    "MetadataEnricherConfig",
    "MetadataEnricherService",
]
