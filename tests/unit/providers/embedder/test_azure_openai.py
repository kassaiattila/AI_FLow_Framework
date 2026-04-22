"""Unit tests for AzureOpenAIEmbedder (Profile B).

@test_registry
suite: unit
tags: [unit, providers, embedder, azure_openai]

The `embed()` round-trip test is skipped when the
`AIFLOW_AZURE_OPENAI__ENDPOINT` / `AIFLOW_AZURE_OPENAI__API_KEY` env vars
are absent — NEVER commit placeholder credentials (Sprint J STOP rule).
"""

from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from aiflow.providers.embedder import AzureOpenAIEmbedder, AzureOpenAIEmbedderConfig
from aiflow.providers.interfaces import EmbedderProvider
from aiflow.providers.metadata import ProviderMetadata


def test_azure_openai_is_embedder_provider_subclass() -> None:
    assert issubclass(AzureOpenAIEmbedder, EmbedderProvider)


def test_azure_openai_metadata_shape() -> None:
    config = AzureOpenAIEmbedderConfig(
        endpoint="https://example.openai.azure.com",
        api_key=SecretStr("dummy-not-used"),
        deployment="text-embedding-3-small",
    )
    embedder = AzureOpenAIEmbedder(config)
    assert isinstance(embedder.metadata, ProviderMetadata)
    assert embedder.metadata.name == "azure_openai"
    assert embedder.metadata.cost_class == "moderate"
    assert embedder.embedding_dim == 1536
    assert embedder.model_name == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_azure_openai_missing_credentials_raises() -> None:
    config = AzureOpenAIEmbedderConfig(endpoint=None, api_key=None)
    embedder = AzureOpenAIEmbedder(config)
    with pytest.raises(RuntimeError, match="AIFLOW_AZURE_OPENAI__ENDPOINT"):
        await embedder.embed(["anything"])


@pytest.mark.asyncio
async def test_azure_openai_embed_real_api() -> None:
    """Round-trip against live Azure OpenAI — skipped unless creds are set."""
    if not (
        os.getenv("AIFLOW_AZURE_OPENAI__ENDPOINT") and os.getenv("AIFLOW_AZURE_OPENAI__API_KEY")
    ):
        pytest.skip(
            "Azure OpenAI credentials not configured — Profile B live test deferred.",
        )
    embedder = AzureOpenAIEmbedder()
    vectors = await embedder.embed(["árvíztűrő tükörfúrógép", "hello world"])
    assert len(vectors) == 2
    assert all(len(v) == embedder.embedding_dim for v in vectors)
    assert all(isinstance(x, float) for x in vectors[0])
