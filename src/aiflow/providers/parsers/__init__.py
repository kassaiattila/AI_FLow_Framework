"""Concrete parser provider implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

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


def register_default_parsers(registry: ProviderRegistry) -> None:
    """Register S95's built-in ParserProvider classes on ``registry``.

    Registration is class-level (no instantiation → no heavy deps imported).
    Consumers (DocumentExtractorService) resolve the class lazily through
    the router's RoutingDecision.
    """
    registry.register_parser(DoclingStandardParser.PROVIDER_NAME, DoclingStandardParser)
    registry.register_parser(UnstructuredParser.PROVIDER_NAME, UnstructuredParser)
