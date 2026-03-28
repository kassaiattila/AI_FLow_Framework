"""
@test_registry:
    suite: core-unit
    component: models.client
    covers: [src/aiflow/models/client.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [models, client, facade, llm]
"""
import pytest
from unittest.mock import AsyncMock
from aiflow.models.client import ModelClient, LLMClient
from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.generation import GenerationOutput
from aiflow.models.protocols.embedding import EmbeddingOutput


@pytest.fixture
def mock_generation_backend():
    backend = AsyncMock()
    backend.generate.return_value = ModelCallResult(
        output=GenerationOutput(text="Hello!", model_used="gpt-4o"),
        model_used="gpt-4o",
        input_tokens=10, output_tokens=5, cost_usd=0.001, latency_ms=500,
    )
    return backend

@pytest.fixture
def mock_embedding_backend():
    backend = AsyncMock()
    backend.embed.return_value = ModelCallResult(
        output=EmbeddingOutput(embeddings=[[0.1, 0.2, 0.3]], dimensions=3, total_tokens=5),
        model_used="text-embedding-3-small",
        input_tokens=5, latency_ms=100,
    )
    return backend

@pytest.fixture
def client(mock_generation_backend, mock_embedding_backend):
    return ModelClient(generation_backend=mock_generation_backend,
                       embedding_backend=mock_embedding_backend)


class TestModelClient:
    @pytest.mark.asyncio
    async def test_generate_calls_backend(self, client, mock_generation_backend):
        result = await client.generate(messages=[{"role": "user", "content": "hi"}])
        assert result.output.text == "Hello!"
        assert result.model_used == "gpt-4o"
        mock_generation_backend.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_model_override(self, client, mock_generation_backend):
        await client.generate(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")
        call_args = mock_generation_backend.generate.call_args[0][0]
        assert call_args.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_generate_with_temperature(self, client, mock_generation_backend):
        await client.generate(messages=[{"role": "user", "content": "hi"}], temperature=0.1)
        call_args = mock_generation_backend.generate.call_args[0][0]
        assert call_args.temperature == 0.1

    @pytest.mark.asyncio
    async def test_embed_calls_backend(self, client, mock_embedding_backend):
        result = await client.embed(texts=["hello world"])
        assert result.output.dimensions == 3
        mock_embedding_backend.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_without_backend_raises(self, mock_generation_backend):
        client = ModelClient(generation_backend=mock_generation_backend, embedding_backend=None)
        with pytest.raises(RuntimeError, match="No embedding backend"):
            await client.embed(texts=["test"])

    @pytest.mark.asyncio
    async def test_generate_returns_cost(self, client):
        result = await client.generate(messages=[{"role": "user", "content": "hi"}])
        assert result.cost_usd == 0.001
        assert result.input_tokens == 10

    def test_llm_client_alias(self):
        assert LLMClient is ModelClient
