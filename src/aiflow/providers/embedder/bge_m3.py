"""BGEM3Embedder — local BGE-M3 EmbedderProvider (Profile A).

Sprint J (v1.4.6 / UC2). The `sentence_transformers` dep + ~2GB BGE-M3 model
are NOT installed by default — the provider resolves them lazily so that
`register_default_embedders` can skip cleanly on environments that haven't
downloaded the model yet. A follow-up session (S101) wires the rag_engine
service against this provider once the model is available locally.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.providers.interfaces import EmbedderProvider
from aiflow.providers.metadata import ProviderMetadata

__all__ = [
    "BGEM3Config",
    "BGEM3Embedder",
]

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL_NAME = "BAAI/bge-m3"
_DEFAULT_DIM = 1024


class BGEM3Config(BaseModel):
    """Runtime config for BGEM3Embedder."""

    model_name: str = Field(
        default=_DEFAULT_MODEL_NAME,
        description="Hugging Face model id passed to SentenceTransformer().",
    )
    cache_folder: str | None = Field(
        default=None,
        description="Local cache directory; falls back to SENTENCE_TRANSFORMERS_HOME.",
    )
    device: str | None = Field(
        default=None,
        description="Torch device hint (e.g. 'cpu', 'cuda:0'). None = auto-detect.",
    )

    @classmethod
    def from_env(cls) -> BGEM3Config:
        return cls(
            model_name=os.getenv("AIFLOW_BGE_M3__MODEL_NAME", _DEFAULT_MODEL_NAME),
            cache_folder=os.getenv("AIFLOW_BGE_M3__CACHE_FOLDER"),
            device=os.getenv("AIFLOW_BGE_M3__DEVICE"),
        )


class BGEM3Embedder(EmbedderProvider):
    """Local Profile A embedder backed by `BAAI/bge-m3` via sentence-transformers."""

    PROVIDER_NAME = "bge_m3"

    def __init__(self, config: BGEM3Config | None = None) -> None:
        self._config = config or BGEM3Config.from_env()
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="1.0",
            supported_types=["text"],
            speed_class="normal",
            gpu_required=False,
            cost_class="free",
            license="MIT",
        )
        self._model: Any | None = None

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    @property
    def embedding_dim(self) -> int:
        return _DEFAULT_DIM

    @property
    def model_name(self) -> str:
        return self._config.model_name

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover — dep-gated
            raise RuntimeError(
                "BGEM3Embedder requires the 'sentence-transformers' extra. "
                "Install with `uv add sentence-transformers` and download the "
                "BAAI/bge-m3 model (~2GB) before using Profile A."
            ) from exc
        self._model = SentenceTransformer(
            self._config.model_name,
            cache_folder=self._config.cache_folder,
            device=self._config.device,
        )
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _do_embed() -> list[list[float]]:
            model = self._load_model()
            vectors = model.encode(texts, normalize_embeddings=True)
            return [list(map(float, v)) for v in vectors]

        result = await asyncio.to_thread(_do_embed)
        logger.info(
            "bge_m3_embed_done",
            model=self._config.model_name,
            batch_size=len(texts),
            dim=self.embedding_dim,
        )
        return result

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._import_check)
        except Exception as exc:
            logger.warning("bge_m3_health_check_failed", error=str(exc))
            return False
        return True

    @staticmethod
    def _import_check() -> None:
        from sentence_transformers import SentenceTransformer  # noqa: F401
