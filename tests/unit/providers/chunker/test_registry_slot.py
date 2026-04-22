"""ProviderRegistry — ChunkerProvider slot unit tests.

@test_registry
suite: unit
tags: [unit, providers, chunker, phase_1_5_sprint_j]
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aiflow.contracts.chunk_result import ChunkResult
from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.providers.interfaces import ChunkerProvider
from aiflow.providers.metadata import ProviderMetadata
from aiflow.providers.registry import ProviderRegistry

_DUMMY_META = ProviderMetadata(
    name="dummy_chunker",
    version="0.1.0",
    supported_types=["text"],
    speed_class="fast",
    cost_class="free",
    license="MIT",
)


class _DummyChunker(ChunkerProvider):
    @property
    def metadata(self) -> ProviderMetadata:
        return _DUMMY_META

    async def chunk(self, parser_result, package_context):  # type: ignore[override]
        return [
            ChunkResult(
                source_file_id=uuid4(),
                package_id=package_context.package_id,
                tenant_id=package_context.tenant_id,
                text="x",
                token_count=1,
                chunk_index=0,
            )
        ]

    async def health_check(self) -> bool:
        return True


def _make_package() -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="t1",
        files=[
            IntakeFile(
                file_path="/tmp/x.pdf",
                file_name="x.pdf",
                mime_type="application/pdf",
                size_bytes=1,
                sha256="a" * 64,
            )
        ],
    )


class TestRegistryChunker:
    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        reg.register_chunker("unstructured", _DummyChunker)
        assert reg.get_chunker("unstructured") is _DummyChunker

    def test_list_chunkers_empty(self) -> None:
        reg = ProviderRegistry()
        assert reg.list_chunkers() == []

    def test_list_chunkers_sorted(self) -> None:
        reg = ProviderRegistry()
        reg.register_chunker("b", _DummyChunker)
        reg.register_chunker("a", _DummyChunker)
        assert reg.list_chunkers() == ["a", "b"]

    def test_get_unregistered_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get_chunker("nonexistent")

    def test_register_non_subclass_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(TypeError, match="subclass of ChunkerProvider"):
            reg.register_chunker("bad", dict)  # type: ignore[arg-type]

    def test_chunker_slot_isolated_from_other_slots(self) -> None:
        """Registering a chunker must not appear in other slots' lists."""
        reg = ProviderRegistry()
        reg.register_chunker("unstructured", _DummyChunker)
        assert reg.list_parsers() == []
        assert reg.list_embedders() == []
        assert reg.list_extractors() == []
        assert reg.list_classifiers() == []


@pytest.mark.asyncio
async def test_dummy_chunker_contract() -> None:
    """Smoke: the dummy chunker satisfies the ABC contract."""
    from aiflow.contracts.parser_result import ParserResult

    chunker = _DummyChunker()
    pkg = _make_package()
    parser_result = ParserResult(file_id=uuid4(), parser_name="docling_standard", text="hi")
    results = await chunker.chunk(parser_result, pkg)
    assert len(results) == 1
    assert results[0].tenant_id == "t1"
    assert await chunker.health_check() is True
    assert isinstance(chunker.metadata, ProviderMetadata)
