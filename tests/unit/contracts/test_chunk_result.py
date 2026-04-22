"""ChunkResult v1 contract — unit tests.

@test_registry
suite: unit_contracts
tags: [unit, contracts, phase_1_5_sprint_j]
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from aiflow.contracts.chunk_result import ChunkResult


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source_file_id": uuid4(),
        "package_id": uuid4(),
        "tenant_id": "tenant_a",
        "text": "hello world",
        "token_count": 3,
        "chunk_index": 0,
    }
    base.update(overrides)
    return base


def test_minimal_chunk_result() -> None:
    kwargs = _kwargs()
    r = ChunkResult(**kwargs)  # type: ignore[arg-type]
    assert r.text == "hello world"
    assert r.token_count == 3
    assert r.chunk_index == 0
    assert r.tenant_id == "tenant_a"
    assert r.metadata == {}
    assert str(r.chunk_id)  # auto-generated UUID


def test_text_required_nonempty() -> None:
    with pytest.raises(ValidationError):
        ChunkResult(**_kwargs(text=""))  # type: ignore[arg-type]


def test_token_count_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        ChunkResult(**_kwargs(token_count=0))  # type: ignore[arg-type]


def test_chunk_index_must_be_nonnegative() -> None:
    with pytest.raises(ValidationError):
        ChunkResult(**_kwargs(chunk_index=-1))  # type: ignore[arg-type]


def test_tenant_id_required_nonempty() -> None:
    with pytest.raises(ValidationError):
        ChunkResult(**_kwargs(tenant_id=""))  # type: ignore[arg-type]


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        ChunkResult(**_kwargs(unknown="x"))  # type: ignore[arg-type]


def test_roundtrip_preserves_metadata() -> None:
    r = ChunkResult(
        **_kwargs(
            metadata={"chunker_name": "unstructured", "chunk_size_tokens": 512},
        )  # type: ignore[arg-type]
    )
    restored = ChunkResult.model_validate(r.model_dump(mode="json"))
    assert restored.metadata == {
        "chunker_name": "unstructured",
        "chunk_size_tokens": 512,
    }
    assert restored.chunk_id == r.chunk_id
    assert restored.source_file_id == r.source_file_id


def test_chunk_ids_unique_across_instances() -> None:
    r1 = ChunkResult(**_kwargs())  # type: ignore[arg-type]
    r2 = ChunkResult(**_kwargs())  # type: ignore[arg-type]
    assert r1.chunk_id != r2.chunk_id
