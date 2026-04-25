"""Unit tests — RAGEngineService._resolve_query_embedder + _QueryEmbedderAdapter.

@test_registry
suite: unit-services-rag-engine
component: aiflow.services.rag_engine.service
covers: [src/aiflow/services/rag_engine/service.py]
phase: v1.5.2
priority: high
requires_services: []
tags: [unit, rag_engine, query, provider_registry, sprint_s, s143]

Sprint S / S143 — closes Sprint J FU-1 (query-path provider registry).

The resolver contract:
* NULL embedder_profile_id → return self._embedder (legacy fallback).
* Known alias (bge_m3 / azure_openai / openai) → return
  _QueryEmbedderAdapter wrapping the concrete EmbedderProvider.
* Unknown alias → raise UnknownEmbedderProfile (not transient).

The adapter contract:
* embed_query(q) awaits provider.embed([q]) and returns the first vector.
* Empty batch → empty list.

No PG, no LLM, no real BGE-M3 weight download — the BGE-M3/AzureOpenAI
classes are not instantiated in these tests; we patch the alias map to
use stub providers so the resolver path is exercised without network or
filesystem I/O.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from aiflow.services.rag_engine.service import (
    CollectionInfo,
    RAGEngineService,
    UnknownEmbedderProfile,
    _QueryEmbedderAdapter,
)


class _StubProvider:
    """Minimal EmbedderProvider duck-type for resolver tests.

    Avoids pulling in BGEM3Embedder (which loads weights on init) or
    AzureOpenAIEmbedder (which reads env creds). Only the surface the
    adapter touches is implemented.
    """

    PROVIDER_NAME = "stub_provider"

    def __init__(self, dim: int = 7, name: str = "stub/model") -> None:
        self._dim = dim
        self._name = name
        self.calls: list[list[str]] = []

    @property
    def embedding_dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.1 * i for i in range(self._dim)] for _ in texts]


def _make_service_with_fallback_embedder(fallback: Any) -> RAGEngineService:
    """Build a RAGEngineService bypassing _start() (no real init)."""
    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = fallback
    return svc


def _coll(profile_id: str | None = None) -> CollectionInfo:
    return CollectionInfo(
        id="c-1",
        name="test-coll",
        embedding_dim=1536,
        tenant_id="default",
        embedder_profile_id=profile_id,
    )


# ---------------------------------------------------------------------------
# _resolve_query_embedder — NULL fallback
# ---------------------------------------------------------------------------


def test_resolver_returns_legacy_embedder_when_profile_id_is_null() -> None:
    legacy = MagicMock(name="legacy_embedder")
    svc = _make_service_with_fallback_embedder(legacy)

    resolved = svc._resolve_query_embedder(_coll(profile_id=None))

    assert resolved is legacy


def test_resolver_null_fallback_works_even_if_provider_aliases_would_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a collection never opts in to ProviderRegistry, alias lookup is
    never consulted — so even a broken alias table can't regress legacy
    collections."""
    legacy = object()
    svc = _make_service_with_fallback_embedder(legacy)

    def _boom() -> None:
        raise RuntimeError("alias table must not be touched when profile is NULL")

    monkeypatch.setattr(
        "aiflow.providers.embedder.BGEM3Embedder",
        _boom,
        raising=True,
    )

    assert svc._resolve_query_embedder(_coll(profile_id=None)) is legacy


# ---------------------------------------------------------------------------
# _resolve_query_embedder — known profiles route through the adapter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alias",
    ["bge_m3", "azure_openai", "openai"],
)
def test_resolver_known_aliases_produce_adapter(
    monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """Patch each concrete class to a cheap stub so we don't load weights
    or reach for Azure credentials. The resolver must return an adapter
    (not the raw provider) so the query() site can call embed_query
    uniformly."""
    svc = _make_service_with_fallback_embedder(MagicMock(name="legacy"))

    class _Stub(_StubProvider):
        PROVIDER_NAME = alias

    monkeypatch.setattr("aiflow.providers.embedder.BGEM3Embedder", _Stub, raising=True)
    monkeypatch.setattr("aiflow.providers.embedder.AzureOpenAIEmbedder", _Stub, raising=True)
    monkeypatch.setattr("aiflow.providers.embedder.OpenAIEmbedder", _Stub, raising=True)

    resolved = svc._resolve_query_embedder(_coll(profile_id=alias))

    assert isinstance(resolved, _QueryEmbedderAdapter)
    # Adapter proxies dim/model_name to the provider.
    assert resolved.embedding_dim == 7
    assert resolved.model_name == "stub/model"


# ---------------------------------------------------------------------------
# _resolve_query_embedder — unknown profile raises
# ---------------------------------------------------------------------------


def test_resolver_unknown_profile_raises_unknown_embedder_profile() -> None:
    svc = _make_service_with_fallback_embedder(MagicMock(name="legacy"))

    with pytest.raises(UnknownEmbedderProfile) as excinfo:
        svc._resolve_query_embedder(_coll(profile_id="nonexistent_provider"))

    # Message lists the registered aliases so operators can self-diagnose.
    msg = str(excinfo.value)
    assert "nonexistent_provider" in msg
    assert "bge_m3" in msg or "azure_openai" in msg or "openai" in msg


def test_unknown_embedder_profile_is_not_transient() -> None:
    """Configuration error — never retry."""
    err = UnknownEmbedderProfile("boom")
    assert err.is_transient is False
    assert err.error_code == "UNKNOWN_EMBEDDER_PROFILE"


# ---------------------------------------------------------------------------
# _QueryEmbedderAdapter — embed_query surface
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_embed_query_returns_first_vector_of_batch() -> None:
    provider = _StubProvider(dim=3)
    adapter = _QueryEmbedderAdapter(provider)

    vec = await adapter.embed_query("hello world")

    assert vec == [0.0, 0.1, 0.2]
    # Adapter batched exactly one text.
    assert provider.calls == [["hello world"]]


@pytest.mark.asyncio
async def test_adapter_embed_query_returns_empty_list_when_provider_yields_empty() -> None:
    class _EmptyProvider(_StubProvider):
        async def embed(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            return []

    adapter = _QueryEmbedderAdapter(_EmptyProvider())
    assert await adapter.embed_query("x") == []


@pytest.mark.asyncio
async def test_adapter_ignores_model_kwarg() -> None:
    """The legacy Embedder.embed_query accepts a ``model`` kwarg; the
    adapter must accept it too for signature compatibility but not pass
    it through (provider has its own pinned model)."""
    provider = _StubProvider(dim=2)
    adapter = _QueryEmbedderAdapter(provider)

    vec = await adapter.embed_query("q", model="ignored-model-name")
    assert len(vec) == 2
    # Provider saw the text, not the model kwarg.
    assert provider.calls == [["q"]]


def test_adapter_proxies_embedding_dim_as_int() -> None:
    adapter = _QueryEmbedderAdapter(_StubProvider(dim=1024))
    assert adapter.embedding_dim == 1024
    assert isinstance(adapter.embedding_dim, int)


def test_adapter_proxies_model_name_as_str() -> None:
    adapter = _QueryEmbedderAdapter(_StubProvider(name="BAAI/bge-m3"))
    assert adapter.model_name == "BAAI/bge-m3"
    assert isinstance(adapter.model_name, str)


# ---------------------------------------------------------------------------
# CollectionInfo — new fields default sanely
# ---------------------------------------------------------------------------


def test_collection_info_defaults_to_default_tenant_and_null_profile() -> None:
    coll = CollectionInfo(id="x", name="y")
    assert coll.tenant_id == "default"
    assert coll.embedder_profile_id is None


def test_collection_info_accepts_explicit_tenant_and_profile() -> None:
    coll = CollectionInfo(
        id="x",
        name="y",
        tenant_id="bestix",
        embedder_profile_id="bge_m3",
    )
    assert coll.tenant_id == "bestix"
    assert coll.embedder_profile_id == "bge_m3"
