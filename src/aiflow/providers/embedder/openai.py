"""OpenAIEmbedder — cloud EmbedderProvider (Profile B surrogate).

Sprint J / UC2 session 4 (v1.4.6 / S103).

Drop-in alternative to :class:`AzureOpenAIEmbedder` that speaks to the public
OpenAI API instead of an Azure deployment. Wired so tenants without an Azure
OpenAI subscription can still run Profile B (cloud paid) via the
``OPENAI_API_KEY`` already present in the project ``.env``.

Defaults to ``text-embedding-3-small`` (1536 dim) to match the existing
``rag_collections.embedding_model`` default, keeping the retrieval layer and
prior ingested data compatible.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field, SecretStr

from aiflow.providers.interfaces import EmbedderProvider
from aiflow.providers.metadata import ProviderMetadata

__all__ = [
    "OpenAIEmbedder",
    "OpenAIEmbedderConfig",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL_NAME = "text-embedding-3-small"
_DEFAULT_DIM = 1536
_DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIEmbedderConfig(BaseModel):
    """Runtime config for OpenAIEmbedder."""

    api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key; falls back to OPENAI_API_KEY env var.",
    )
    model_name: str = Field(
        default=_DEFAULT_MODEL_NAME,
        description="Embedding model name (text-embedding-3-small / -large / -ada-002).",
    )
    base_url: str = Field(
        default=_DEFAULT_BASE_URL,
        description="OpenAI API base URL; override for proxies.",
    )
    embedding_dim: int = Field(
        default=_DEFAULT_DIM,
        description="Expected embedding dimensionality (1536 for -3-small/-ada-002).",
    )
    timeout_seconds: float = Field(default=30.0)

    @classmethod
    def from_env(cls) -> OpenAIEmbedderConfig:
        return cls(
            api_key=(
                SecretStr(os.environ["OPENAI_API_KEY"]) if "OPENAI_API_KEY" in os.environ else None
            ),
            model_name=os.getenv("AIFLOW_OPENAI__EMBEDDING_MODEL", _DEFAULT_MODEL_NAME),
            base_url=os.getenv("AIFLOW_OPENAI__BASE_URL", _DEFAULT_BASE_URL),
            embedding_dim=int(os.getenv("AIFLOW_OPENAI__EMBEDDING_DIM", str(_DEFAULT_DIM))),
        )


class OpenAIEmbedder(EmbedderProvider):
    """Cloud Profile B embedder backed by OpenAI's public embeddings API."""

    PROVIDER_NAME = "openai"

    def __init__(self, config: OpenAIEmbedderConfig | None = None) -> None:
        self._config = config or OpenAIEmbedderConfig.from_env()
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="1.0",
            supported_types=["text"],
            speed_class="fast",
            gpu_required=False,
            cost_class="moderate",
            license="proprietary",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    @property
    def embedding_dim(self) -> int:
        return self._config.embedding_dim

    @property
    def model_name(self) -> str:
        return self._config.model_name

    def _resolve_api_key(self) -> str:
        if self._config.api_key is not None:
            return self._config.api_key.get_secret_value()
        env_key = os.getenv("OPENAI_API_KEY")
        if not env_key:
            raise RuntimeError("OpenAIEmbedder requires OPENAI_API_KEY to be configured.")
        return env_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        api_key = self._resolve_api_key()
        url = f"{self._config.base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._config.model_name,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        vectors = [item["embedding"] for item in data.get("data", [])]
        if len(vectors) != len(texts):
            raise RuntimeError(f"OpenAIEmbedder expected {len(texts)} vectors, got {len(vectors)}.")

        logger.info(
            "openai_embed_done",
            model=self._config.model_name,
            batch_size=len(texts),
            dim=len(vectors[0]) if vectors else 0,
        )
        return vectors

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._resolve_api_key)
        except Exception as exc:
            logger.warning("openai_health_check_failed", error=str(exc))
            return False
        return True
