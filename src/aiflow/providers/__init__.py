"""Provider abstraction — pluggable parser/classifier/extractor/embedder.

Source: 103_AIFLOW_v2_FINAL_VALIDATION.md Section 5 (MF6),
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.6-5.10
"""

from aiflow.providers.interfaces import (
    ClassifierProvider,
    EmbedderProvider,
    ExtractorProvider,
    ParserProvider,
)
from aiflow.providers.metadata import ProviderMetadata
from aiflow.providers.registry import ProviderRegistry

__all__ = [
    "ClassifierProvider",
    "EmbedderProvider",
    "ExtractorProvider",
    "ParserProvider",
    "ProviderMetadata",
    "ProviderRegistry",
]
