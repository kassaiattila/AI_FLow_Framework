"""Embedder provider implementations.

Exposes the :class:`EmbedderProvider` ABC plus concrete BGE-M3 (Profile A)
and Azure OpenAI (Profile B) embedders. Sprint J (v1.4.6) — UC2 RAG kickoff.
"""

from aiflow.providers.embedder.azure_openai import (
    AzureOpenAIEmbedder,
    AzureOpenAIEmbedderConfig,
)
from aiflow.providers.embedder.bge_m3 import BGEM3Config, BGEM3Embedder
from aiflow.providers.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from aiflow.providers.interfaces import EmbedderProvider

__all__ = [
    "AzureOpenAIEmbedder",
    "AzureOpenAIEmbedderConfig",
    "BGEM3Config",
    "BGEM3Embedder",
    "EmbedderProvider",
    "OpenAIEmbedder",
    "OpenAIEmbedderConfig",
]
