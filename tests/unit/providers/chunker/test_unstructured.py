"""UnstructuredChunker unit tests.

@test_registry
suite: unit
tags: [unit, providers, chunker, phase_1_5_sprint_j]

Exercises the Sprint J UnstructuredChunker against realistic insurance-doc
style Hungarian text (the UC2 target domain). The chunker operates on
``ParserResult.text``, so the tests feed it a ``ParserResult`` carrying a
long multi-paragraph blob rather than re-running a real PDF parse — the
parser↔chunker integration is covered end-to-end by the Step 3 integration
test using real PDFs from ``e2e-audit/test-data/rag-docs/``.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aiflow.contracts.parser_result import ParserResult
from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.providers.chunker.unstructured import (
    UnstructuredChunker,
    UnstructuredChunkerConfig,
)
from aiflow.providers.interfaces import ChunkerProvider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LONG_TEXT = (
    "Az Allianz Gondoskodás Programok biztosítási szerződés keretében "
    "a biztosító vállalja, hogy a szerződésben meghatározott feltételek "
    "szerint a biztosítási esemény bekövetkezése esetén a szerződés "
    "szerinti szolgáltatást teljesíti a biztosított vagy kedvezményezett "
    "részére. A szerződés tartama alatt a biztosítási díj megfizetése a "
    "szerződő kötelezettsége.\n\n"
    "A biztosítási esemény a biztosított halála, baleseti eredetű "
    "maradandó egészségkárosodása, vagy a szerződésben rögzített egyéb "
    "esemény bekövetkezése. A biztosító a biztosítási esemény "
    "bejelentését követően 15 munkanapon belül teljesíti a szolgáltatást, "
    "amennyiben minden szükséges dokumentum rendelkezésre áll.\n\n"
    "A szerződő a szerződést írásban, 30 napos felmondási idővel mondhatja "
    "fel a biztosítási év végére. A felmondás jogát a szerződő a "
    "szerződéskötéstől számított 14 napon belül is gyakorolhatja, ekkor a "
    "biztosító a megfizetett díjat visszafizeti.\n\n"
    "A biztosítási szerződés megszűnik, ha a szerződő a díjfizetéssel "
    "60 napot meghaladó késedelembe esik, és a biztosító ismételt "
    "felszólítása ellenére sem fizeti meg az elmaradt díjat. A szerződés "
    "megszűnésével a biztosító szolgáltatási kötelezettsége is megszűnik."
) * 4  # ~4x-ed to ensure we exceed the 512-token window handily


def _make_package() -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_sprint_j",
        files=[
            IntakeFile(
                file_path="/tmp/test.pdf",
                file_name="test.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                sha256="a" * 64,
            )
        ],
    )


def _make_parser_result(text: str = _LONG_TEXT) -> ParserResult:
    return ParserResult(
        file_id=uuid4(),
        parser_name="docling_standard",
        text=text,
        page_count=3,
    )


# ---------------------------------------------------------------------------
# Type / metadata smoke
# ---------------------------------------------------------------------------


def test_unstructured_chunker_is_provider_subclass() -> None:
    assert issubclass(UnstructuredChunker, ChunkerProvider)


def test_unstructured_chunker_metadata() -> None:
    chunker = UnstructuredChunker()
    assert chunker.metadata.name == "unstructured"
    assert "text" in chunker.metadata.supported_types
    assert chunker.metadata.cost_class == "free"


def test_overlap_larger_than_size_rejected() -> None:
    with pytest.raises(ValueError, match="overlap_tokens"):
        UnstructuredChunker(
            UnstructuredChunkerConfig(chunk_size_tokens=100, overlap_tokens=200),
        )


# ---------------------------------------------------------------------------
# Behavioural tests against a realistic ParserResult
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chunk_produces_at_least_one_chunk() -> None:
    chunker = UnstructuredChunker()
    parser_result = _make_parser_result()
    pkg = _make_package()

    chunks = await chunker.chunk(parser_result, pkg)

    assert len(chunks) >= 1
    for c in chunks:
        assert c.tenant_id == "tenant_sprint_j"
        assert c.source_file_id == parser_result.file_id
        assert c.package_id == pkg.package_id
        assert c.token_count > 0
        assert c.metadata["chunker_name"] == "unstructured"
        assert c.metadata["parser_name"] == "docling_standard"


@pytest.mark.asyncio
async def test_chunk_indices_are_monotonic() -> None:
    chunker = UnstructuredChunker()
    chunks = await chunker.chunk(_make_parser_result(), _make_package())
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


@pytest.mark.asyncio
async def test_chunks_preserve_overlap_between_neighbours() -> None:
    """With overlap > 0 and text longer than the window, at least one token
    from the previous chunk must reappear at the start of the next chunk."""
    chunker = UnstructuredChunker(
        UnstructuredChunkerConfig(chunk_size_tokens=128, overlap_tokens=32),
    )
    chunks = await chunker.chunk(_make_parser_result(), _make_package())

    # The long fixture must produce ≥2 chunks under a 128-token window.
    assert len(chunks) >= 2

    # Use tiktoken when available for an exact overlap check; otherwise
    # fall back to a character-level intersection (simple fallback path).
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        prev_tail = enc.encode(chunks[0].text)[-32:]
        next_head = enc.encode(chunks[1].text)[:32]
        # At least one token should overlap; we don't require an exact
        # prefix match because token boundary shifts across chunk splits.
        assert set(prev_tail) & set(next_head)
    except ImportError:
        assert chunks[0].text[-20:] in chunks[1].text[: len(chunks[0].text[-20:]) + 200]


@pytest.mark.asyncio
async def test_empty_text_returns_empty_list() -> None:
    chunker = UnstructuredChunker()
    parser_result = ParserResult(file_id=uuid4(), parser_name="docling_standard", text="  \n\n  ")
    chunks = await chunker.chunk(parser_result, _make_package())
    assert chunks == []


@pytest.mark.asyncio
async def test_health_check_returns_true() -> None:
    chunker = UnstructuredChunker()
    assert await chunker.health_check() is True
