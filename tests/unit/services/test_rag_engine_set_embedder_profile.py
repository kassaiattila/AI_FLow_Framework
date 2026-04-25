"""Unit tests — RAGEngineService.set_embedder_profile() + DimensionMismatch.

@test_registry
suite: unit-services-rag-engine
component: aiflow.services.rag_engine.service
covers: [src/aiflow/services/rag_engine/service.py]
phase: v1.5.2
priority: high
requires_services: []
tags: [unit, rag_engine, mutation, dim_guard, sprint_s, s144]

Sprint S / S144 — admin UI mutation: attach / detach embedder profile.

Contract:
* Unknown collection_id → returns None (no exception).
* Unknown alias (not in {None, bge_m3, azure_openai, openai}) →
  raises UnknownEmbedderProfile.
* chunk_count == 0 → any known alias is accepted, embedding_dim is
  refreshed to the new provider's dim.
* chunk_count > 0 → new dim MUST equal the existing embedding_dim, else
  DimensionMismatch (HTTP 409). Detaching to NULL on a non-1536 collection
  is also a DimensionMismatch because the legacy self._embedder is pinned
  at OpenAI 1536-dim.

No PG, no LLM, no real BGE-M3 weight download — provider classes are
monkeypatched with stub doubles, the session_factory is replaced with a
recording fake.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from aiflow.services.rag_engine.service import (
    CollectionInfo,
    DimensionMismatch,
    RAGEngineService,
    UnknownEmbedderProfile,
)


class _StubProvider:
    """Cheap EmbedderProvider stand-in with adjustable dim."""

    PROVIDER_NAME = "stub"

    def __init__(self, dim: int = 1536) -> None:
        self._dim = dim

    @property
    def embedding_dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "stub/model"


class _FakeSession:
    """Async-context-manager session that records executed SQL."""

    def __init__(self, recorder: list[tuple[str, dict[str, Any]]]) -> None:
        self._recorder = recorder

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> Any:
        self._recorder.append((str(stmt), params or {}))
        return MagicMock()

    async def commit(self) -> None:
        return None


def _make_session_factory(recorder: list[tuple[str, dict[str, Any]]]):
    def _factory() -> _FakeSession:
        return _FakeSession(recorder)

    return _factory


def _make_service(
    coll_lookup: dict[str, CollectionInfo | None],
    recorder: list[tuple[str, dict[str, Any]]] | None = None,
) -> RAGEngineService:
    """Build a RAGEngineService bypassing _start(), with monkeyable get_collection."""
    if recorder is None:
        recorder = []
    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = MagicMock(name="legacy_embedder")
    svc._session_factory = _make_session_factory(recorder)  # type: ignore[assignment]
    svc._logger = MagicMock(name="logger")

    call_count = {"n": 0}

    async def _fake_get_collection(cid: str) -> CollectionInfo | None:
        call_count["n"] += 1
        return coll_lookup.get(cid)

    svc.get_collection = _fake_get_collection  # type: ignore[method-assign]
    svc._get_collection_calls = call_count  # type: ignore[attr-defined]
    return svc


def _coll(
    *,
    chunk_count: int = 0,
    embedding_dim: int = 1536,
    profile_id: str | None = None,
) -> CollectionInfo:
    return CollectionInfo(
        id="c-1",
        name="test-coll",
        embedding_dim=embedding_dim,
        chunk_count=chunk_count,
        tenant_id="default",
        embedder_profile_id=profile_id,
    )


def _patch_provider_classes(monkeypatch: pytest.MonkeyPatch, dim: int) -> None:
    """Patch all three concrete embedder classes — each keeps its own
    PROVIDER_NAME so the service's alias-keyed dict doesn't collapse three
    classes into one."""

    def _make_stub(alias: str) -> type[_StubProvider]:
        class _Stub(_StubProvider):
            PROVIDER_NAME = alias

            def __init__(self) -> None:  # zero-arg
                super().__init__(dim=dim)

        return _Stub

    monkeypatch.setattr(
        "aiflow.providers.embedder.BGEM3Embedder", _make_stub("bge_m3"), raising=True
    )
    monkeypatch.setattr(
        "aiflow.providers.embedder.AzureOpenAIEmbedder",
        _make_stub("azure_openai"),
        raising=True,
    )
    monkeypatch.setattr(
        "aiflow.providers.embedder.OpenAIEmbedder", _make_stub("openai"), raising=True
    )


# ---------------------------------------------------------------------------
# Unknown collection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_collection_returns_none() -> None:
    svc = _make_service({})

    result = await svc.set_embedder_profile("nope", "bge_m3")

    assert result is None


# ---------------------------------------------------------------------------
# Unknown alias
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_alias_raises_unknown_embedder_profile() -> None:
    svc = _make_service({"c-1": _coll(chunk_count=0)})

    with pytest.raises(UnknownEmbedderProfile) as excinfo:
        await svc.set_embedder_profile("c-1", "nonexistent_provider")

    msg = str(excinfo.value)
    assert "nonexistent_provider" in msg
    assert "bge_m3" in msg


# ---------------------------------------------------------------------------
# Empty collection — any profile accepted, embedding_dim refreshed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_collection_accepts_new_profile_and_updates_dim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider_classes(monkeypatch, dim=1024)

    coll_before = _coll(chunk_count=0, embedding_dim=1536, profile_id=None)
    coll_after = _coll(chunk_count=0, embedding_dim=1024, profile_id="bge_m3")
    lookup_state = {"calls": 0}

    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = MagicMock()
    recorder: list[tuple[str, dict[str, Any]]] = []
    svc._session_factory = _make_session_factory(recorder)  # type: ignore[assignment]
    svc._logger = MagicMock()

    async def _fake_get(cid: str) -> CollectionInfo | None:
        lookup_state["calls"] += 1
        return coll_before if lookup_state["calls"] == 1 else coll_after

    svc.get_collection = _fake_get  # type: ignore[method-assign]

    result = await svc.set_embedder_profile("c-1", "bge_m3")

    assert result is coll_after
    sql_blobs = " | ".join(stmt for stmt, _ in recorder)
    assert "embedder_profile_id = :p" in sql_blobs
    assert "embedding_dim = :dim" in sql_blobs
    dim_update = next(p for stmt, p in recorder if "embedding_dim = :dim" in stmt)
    assert dim_update["dim"] == 1024


# ---------------------------------------------------------------------------
# Non-empty collection — dim-equal accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_empty_collection_accepts_dim_equal_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider_classes(monkeypatch, dim=1536)

    coll = _coll(chunk_count=42, embedding_dim=1536, profile_id=None)
    svc = _make_service({"c-1": coll})

    result = await svc.set_embedder_profile("c-1", "openai")

    # get_collection is called twice: once for guard, once for return snapshot.
    assert svc._get_collection_calls["n"] == 2  # type: ignore[attr-defined]
    assert result is coll  # second lookup also returns the same object in this fake


# ---------------------------------------------------------------------------
# Non-empty collection — dim-mismatch on attach raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_empty_collection_rejects_dim_mismatch_on_attach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider_classes(monkeypatch, dim=1024)  # bge_m3-style

    coll = _coll(chunk_count=42, embedding_dim=1536, profile_id=None)
    recorder: list[tuple[str, dict[str, Any]]] = []
    svc = _make_service({"c-1": coll}, recorder=recorder)

    with pytest.raises(DimensionMismatch) as excinfo:
        await svc.set_embedder_profile("c-1", "bge_m3")

    msg = str(excinfo.value)
    assert "1536" in msg and "1024" in msg
    # Guard fired BEFORE any UPDATE — recorder must be empty.
    assert recorder == []


# ---------------------------------------------------------------------------
# Non-empty collection — detach (→NULL) on non-1536 collection raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_empty_collection_rejects_detach_when_dim_not_1536() -> None:
    coll = _coll(chunk_count=10, embedding_dim=1024, profile_id="bge_m3")
    recorder: list[tuple[str, dict[str, Any]]] = []
    svc = _make_service({"c-1": coll}, recorder=recorder)

    with pytest.raises(DimensionMismatch) as excinfo:
        await svc.set_embedder_profile("c-1", None)

    msg = str(excinfo.value)
    assert "1024" in msg and "1536" in msg
    assert recorder == []


# ---------------------------------------------------------------------------
# Non-empty collection — detach (→NULL) on 1536 collection accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_empty_collection_accepts_detach_when_dim_is_1536() -> None:
    coll_before = _coll(chunk_count=10, embedding_dim=1536, profile_id="openai")
    coll_after = _coll(chunk_count=10, embedding_dim=1536, profile_id=None)
    state = {"calls": 0}

    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = MagicMock()
    recorder: list[tuple[str, dict[str, Any]]] = []
    svc._session_factory = _make_session_factory(recorder)  # type: ignore[assignment]
    svc._logger = MagicMock()

    async def _fake_get(cid: str) -> CollectionInfo | None:
        state["calls"] += 1
        return coll_before if state["calls"] == 1 else coll_after

    svc.get_collection = _fake_get  # type: ignore[method-assign]

    result = await svc.set_embedder_profile("c-1", None)

    assert result is coll_after
    # Exactly one UPDATE — embedding_dim must NOT have been touched.
    sqls = [stmt for stmt, _ in recorder]
    assert any("embedder_profile_id = :p" in s for s in sqls)
    assert not any("embedding_dim = :dim" in s for s in sqls)


# ---------------------------------------------------------------------------
# Non-empty collection — switch profile dim-equal accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_empty_collection_accepts_profile_to_profile_dim_equal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider_classes(monkeypatch, dim=1536)

    coll_before = _coll(chunk_count=5, embedding_dim=1536, profile_id="openai")
    coll_after = _coll(chunk_count=5, embedding_dim=1536, profile_id="azure_openai")
    state = {"calls": 0}

    svc = RAGEngineService.__new__(RAGEngineService)
    svc._embedder = MagicMock()
    recorder: list[tuple[str, dict[str, Any]]] = []
    svc._session_factory = _make_session_factory(recorder)  # type: ignore[assignment]
    svc._logger = MagicMock()

    async def _fake_get(cid: str) -> CollectionInfo | None:
        state["calls"] += 1
        return coll_before if state["calls"] == 1 else coll_after

    svc.get_collection = _fake_get  # type: ignore[method-assign]

    result = await svc.set_embedder_profile("c-1", "azure_openai")

    assert result is coll_after
    # No embedding_dim UPDATE because dim already matches.
    sqls = [stmt for stmt, _ in recorder]
    assert not any("embedding_dim = :dim" in s for s in sqls)


# ---------------------------------------------------------------------------
# DimensionMismatch error metadata
# ---------------------------------------------------------------------------


def test_dimension_mismatch_error_metadata() -> None:
    err = DimensionMismatch("oops")

    assert err.is_transient is False
    assert err.error_code == "RAG_DIM_MISMATCH"
    assert err.http_status == 409
