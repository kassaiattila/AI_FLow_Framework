"""Embedding generation wrapper for vector store operations."""
from typing import Any
import structlog
from aiflow.models.client import ModelClient
from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.embedding import EmbeddingOutput

__all__ = ["Embedder"]
logger = structlog.get_logger(__name__)

class Embedder:
    """Generates embeddings using ModelClient. Used by ingestion pipeline and search."""

    def __init__(self, model_client: ModelClient, default_model: str = "openai/text-embedding-3-small") -> None:
        self._client = model_client
        self._default_model = default_model

    async def embed_texts(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        result = await self._client.embed(texts, model=model or self._default_model)
        logger.info("texts_embedded", count=len(texts), dimensions=result.output.dimensions,
                     model=result.model_used)
        return result.output.embeddings

    async def embed_query(self, query: str, *, model: str | None = None) -> list[float]:
        """Generate embedding for a single query."""
        embeddings = await self.embed_texts([query], model=model)
        return embeddings[0] if embeddings else []

    @property
    def default_model(self) -> str:
        return self._default_model
