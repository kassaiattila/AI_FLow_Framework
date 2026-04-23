"""AzureOpenAIEmbedder — cloud EmbedderProvider (Profile B).

Wraps Azure OpenAI's ``text-embedding-3-small`` (default) behind the
`openai` SDK's ``AzureOpenAI`` client. Sprint J (v1.4.6 / UC2). Policy-gated:
the router only routes here when the tenant policy allows cloud AI AND the
``AIFLOW_AZURE_OPENAI__ENDPOINT`` / ``AIFLOW_AZURE_OPENAI__API_KEY`` env vars
are present. Follows the AzureDocumentIntelligenceParser convention from S96.
"""

from __future__ import annotations

import asyncio
import os

import structlog
from pydantic import BaseModel, Field, SecretStr

from aiflow.providers.interfaces import EmbedderProvider
from aiflow.providers.metadata import ProviderMetadata

__all__ = [
    "AzureOpenAIEmbedderConfig",
    "AzureOpenAIEmbedder",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "text-embedding-3-small"
_DEFAULT_DIM = 1536
_DEFAULT_API_VERSION = "2024-02-01"


class AzureOpenAIEmbedderConfig(BaseModel):
    """Runtime config for AzureOpenAIEmbedder."""

    endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL; falls back to AIFLOW_AZURE_OPENAI__ENDPOINT.",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Azure OpenAI key; falls back to AIFLOW_AZURE_OPENAI__API_KEY.",
    )
    api_version: str = Field(
        default=_DEFAULT_API_VERSION,
        description="Azure OpenAI API version.",
    )
    deployment: str = Field(
        default=_DEFAULT_MODEL,
        description="Azure deployment name (maps 1:1 to the model).",
    )
    timeout_s: int = Field(
        default=60,
        ge=1,
        description="Per-request wall clock timeout (seconds).",
    )

    @classmethod
    def from_env(cls) -> AzureOpenAIEmbedderConfig:
        from aiflow.security.resolver import get_secret_manager

        api_key = get_secret_manager().get_secret(
            "llm/azure_openai#api_key", env_alias="AIFLOW_AZURE_OPENAI__API_KEY"
        )
        return cls(
            endpoint=os.getenv("AIFLOW_AZURE_OPENAI__ENDPOINT"),
            api_key=SecretStr(api_key) if api_key else None,
            api_version=os.getenv(
                "AIFLOW_AZURE_OPENAI__API_VERSION",
                _DEFAULT_API_VERSION,
            ),
            deployment=os.getenv(
                "AIFLOW_AZURE_OPENAI__EMBEDDING_DEPLOYMENT",
                _DEFAULT_MODEL,
            ),
        )


class AzureOpenAIEmbedder(EmbedderProvider):
    """Cloud Profile B embedder backed by Azure OpenAI embeddings."""

    PROVIDER_NAME = "azure_openai"

    def __init__(self, config: AzureOpenAIEmbedderConfig | None = None) -> None:
        self._config = config or AzureOpenAIEmbedderConfig.from_env()
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="1.0",
            supported_types=["text"],
            speed_class="normal",
            gpu_required=False,
            cost_class="moderate",
            license="commercial",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    @property
    def embedding_dim(self) -> int:
        return _DEFAULT_DIM

    @property
    def model_name(self) -> str:
        return self._config.deployment

    def _resolve_credentials(self) -> tuple[str, str]:
        from aiflow.security.resolver import get_secret_manager

        endpoint = self._config.endpoint or os.getenv("AIFLOW_AZURE_OPENAI__ENDPOINT")
        if self._config.api_key is not None:
            key: str | None = self._config.api_key.get_secret_value()
        else:
            key = get_secret_manager().get_secret(
                "llm/azure_openai#api_key", env_alias="AIFLOW_AZURE_OPENAI__API_KEY"
            )
        if not endpoint or not key:
            raise RuntimeError(
                "AzureOpenAIEmbedder requires both AIFLOW_AZURE_OPENAI__ENDPOINT "
                "and AIFLOW_AZURE_OPENAI__API_KEY (or kv/aiflow/llm/azure_openai#api_key)."
            )
        return endpoint, key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        endpoint, key = self._resolve_credentials()
        api_version = self._config.api_version
        deployment = self._config.deployment
        timeout_s = self._config.timeout_s

        def _do_embed() -> list[list[float]]:
            from openai import AzureOpenAI

            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=key,
                api_version=api_version,
                timeout=float(timeout_s),
            )
            response = client.embeddings.create(
                model=deployment,
                input=texts,
            )
            return [list(map(float, item.embedding)) for item in response.data]

        vectors = await asyncio.to_thread(_do_embed)
        logger.info(
            "azure_openai_embed_done",
            deployment=deployment,
            batch_size=len(texts),
            dim=self.embedding_dim,
        )
        return vectors

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._import_check)
        except Exception as exc:
            logger.warning("azure_openai_health_check_failed", error=str(exc))
            return False
        try:
            endpoint, key = self._resolve_credentials()
        except RuntimeError:
            return False
        return bool(endpoint and key)

    @staticmethod
    def _import_check() -> None:
        from openai import AzureOpenAI  # noqa: F401
