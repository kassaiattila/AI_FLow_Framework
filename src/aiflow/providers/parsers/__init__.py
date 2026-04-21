"""Concrete parser provider implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from aiflow.providers.parsers.docling_standard import (
    DoclingConfig,
    DoclingStandardParser,
)
from aiflow.providers.parsers.unstructured_fast import UnstructuredParser

if TYPE_CHECKING:
    from aiflow.providers.registry import ProviderRegistry

__all__ = [
    "DoclingConfig",
    "DoclingStandardParser",
    "UnstructuredParser",
    "register_default_parsers",
]

_logger = structlog.get_logger(__name__)


def register_default_parsers(registry: ProviderRegistry) -> None:
    """Register S95+S96 built-in ParserProvider classes on ``registry``.

    Registration is class-level (no instantiation → no heavy deps imported).
    The Azure DI parser is registered conditionally — if its optional extra
    is not installed, we simply skip it so tenants without cloud AI keep
    working unchanged.
    """
    registry.register_parser(DoclingStandardParser.PROVIDER_NAME, DoclingStandardParser)
    registry.register_parser(UnstructuredParser.PROVIDER_NAME, UnstructuredParser)

    try:
        import azure.ai.documentintelligence  # noqa: F401
    except ImportError as exc:
        _logger.info(
            "azure_di_parser_not_registered",
            reason="optional_extra_missing",
            error=str(exc),
        )
        return

    from aiflow.providers.parsers.azure_document_intelligence import (
        AzureDocumentIntelligenceParser,
    )

    registry.register_parser(
        AzureDocumentIntelligenceParser.PROVIDER_NAME,
        AzureDocumentIntelligenceParser,
    )
