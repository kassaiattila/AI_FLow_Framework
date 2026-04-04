"""Document Extractor service — configurable document field extraction."""

from aiflow.services.document_extractor.service import (
    DocumentExtractorConfig,
    DocumentExtractorService,
    DocumentTypeConfig,
    ExtractionResult,
    FieldDefinition,
)
from aiflow.services.document_extractor.free_text import (
    FreeTextExtractorConfig,
    FreeTextExtractorService,
    FreeTextExtractionResponse,
    FreeTextQuery,
    FreeTextResult,
)

__all__ = [
    "DocumentExtractorConfig",
    "DocumentExtractorService",
    "DocumentTypeConfig",
    "ExtractionResult",
    "FieldDefinition",
    "FreeTextExtractorConfig",
    "FreeTextExtractorService",
    "FreeTextExtractionResponse",
    "FreeTextQuery",
    "FreeTextResult",
]
