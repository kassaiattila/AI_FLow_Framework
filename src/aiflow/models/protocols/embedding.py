"""Embedding protocol for vector representations."""
from abc import abstractmethod

from pydantic import BaseModel

from aiflow.models.protocols.base import BaseModelProtocol, ModelCallResult

__all__ = ["EmbeddingInput", "EmbeddingOutput", "EmbeddingProtocol"]


class EmbeddingInput(BaseModel):
    """Input for embedding generation."""
    texts: list[str]
    model: str | None = None


class EmbeddingOutput(BaseModel):
    """Output from embedding generation."""
    embeddings: list[list[float]]
    dimensions: int
    total_tokens: int = 0


class EmbeddingProtocol(BaseModelProtocol):
    """Protocol for text embedding generation."""

    @abstractmethod
    async def embed(
        self,
        input_data: EmbeddingInput,
    ) -> ModelCallResult[EmbeddingOutput]:
        """Generate embeddings for texts."""
        ...
