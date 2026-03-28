"""
@test_registry:
    suite: vectorstore-unit
    component: vectorstore.embedder
    covers: [src/aiflow/vectorstore/embedder.py]
    phase: 2
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [vectorstore, embedder, embedding]
"""
import pytest
from unittest.mock import AsyncMock
from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.embedding import EmbeddingOutput
from aiflow.vectorstore.embedder import Embedder

@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.embed.return_value = ModelCallResult(
        output=EmbeddingOutput(embeddings=[[0.1, 0.2, 0.3]], dimensions=3, total_tokens=5),
        model_used="text-embedding-3-small", input_tokens=5, latency_ms=100,
    )
    return client

class TestEmbedder:
    @pytest.mark.asyncio
    async def test_embed_texts(self, mock_client):
        embedder = Embedder(mock_client)
        result = await embedder.embed_texts(["hello", "world"])
        assert len(result) == 1  # mock returns 1 embedding
        mock_client.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_empty(self, mock_client):
        embedder = Embedder(mock_client)
        result = await embedder.embed_texts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_query(self, mock_client):
        embedder = Embedder(mock_client)
        result = await embedder.embed_query("what is this?")
        assert len(result) == 3  # 3 dimensions

    def test_default_model(self, mock_client):
        embedder = Embedder(mock_client)
        assert "embedding" in embedder.default_model

    def test_custom_model(self, mock_client):
        embedder = Embedder(mock_client, default_model="custom/model")
        assert embedder.default_model == "custom/model"
