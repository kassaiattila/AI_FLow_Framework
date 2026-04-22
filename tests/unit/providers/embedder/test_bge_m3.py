"""Unit tests for BGEM3Embedder (Profile A).

@test_registry
suite: unit
tags: [unit, providers, embedder, bge_m3]

Skipped automatically when `sentence_transformers` is not installed OR when
the BAAI/bge-m3 weights haven't been downloaded yet (Profile A bootstrap is
deferred to S101 per the Sprint J kickoff plan).
"""

from __future__ import annotations

import pytest

from aiflow.providers.embedder import BGEM3Config, BGEM3Embedder
from aiflow.providers.interfaces import EmbedderProvider
from aiflow.providers.metadata import ProviderMetadata


def test_bge_m3_is_embedder_provider_subclass() -> None:
    assert issubclass(BGEM3Embedder, EmbedderProvider)


def test_bge_m3_metadata_shape() -> None:
    embedder = BGEM3Embedder(
        BGEM3Config(model_name="BAAI/bge-m3", cache_folder=None, device="cpu"),
    )
    assert isinstance(embedder.metadata, ProviderMetadata)
    assert embedder.metadata.name == "bge_m3"
    assert embedder.metadata.cost_class == "free"
    assert embedder.metadata.license == "MIT"
    assert embedder.embedding_dim == 1024
    assert embedder.model_name == "BAAI/bge-m3"


@pytest.mark.asyncio
async def test_bge_m3_embed_real_model() -> None:
    """Real BGE-M3 embedding — skipped unless sentence-transformers is installed."""
    pytest.importorskip(
        "sentence_transformers",
        reason="Profile A deps not installed — defer to S101 per Sprint J plan.",
    )
    embedder = BGEM3Embedder()
    try:
        vectors = await embedder.embed(["hello world", "árvíztűrő tükörfúrógép"])
    except (OSError, RuntimeError) as exc:  # pragma: no cover — offline cache miss
        pytest.skip(f"BGE-M3 weights unavailable locally: {exc}")
    assert len(vectors) == 2
    assert all(len(v) == embedder.embedding_dim for v in vectors)
    assert all(isinstance(x, float) for x in vectors[0])
