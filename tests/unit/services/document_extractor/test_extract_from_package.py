"""DocumentExtractorService.extract_from_package() — unit tests.

@test_registry
suite: unit_services_document_extractor
tags: [unit, services, document_extractor, sprint_i, phase_1_5]

Scope: UC1 session 1 (S94 v1.4.5.1). Uses in-memory fakes for PolicyEngine
and ParserProvider — DB-less. Real integration test lives in
tests/integration/services/document_extractor/.
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID, uuid4

import pytest

from aiflow.contracts.extraction_result import ExtractionResult
from aiflow.contracts.parser_result import ParserResult
from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.providers.interfaces import ParserProvider
from aiflow.providers.metadata import ProviderMetadata
from aiflow.services.document_extractor.service import (
    DocumentExtractorConfig,
    DocumentExtractorService,
)

# --- Fakes -----------------------------------------------------------------


class FakeParser(ParserProvider):
    PROVIDER_NAME = "docling_standard"

    def __init__(self, text: str = "hello parsed", pages: int = 1) -> None:
        self._text = text
        self._pages = pages
        self.calls: list[tuple[UUID, UUID]] = []

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="docling_standard",
            version="test",
            supported_types=["pdf"],
            speed_class="fast",
            cost_class="free",
            license="MIT",
        )

    async def parse(self, file: IntakeFile, package_context: IntakePackage) -> ParserResult:
        self.calls.append((package_context.package_id, file.file_id))
        return ParserResult(
            file_id=file.file_id,
            parser_name="docling_standard",
            text=self._text,
            markdown=self._text,
            tables=[{"index": 0, "markdown": "| a | b |"}] if self._pages else [],
            page_count=self._pages,
            parse_duration_ms=1.0,
        )

    async def health_check(self) -> bool:
        return True

    async def estimate_cost(self, file: IntakeFile) -> float:
        return 0.0


class _FakePolicyConfig:
    def __init__(self, cloud_ai_allowed: bool = False) -> None:
        self.cloud_ai_allowed = cloud_ai_allowed


class _FakePolicyEngine:
    def __init__(self, cloud_ai_allowed: bool = False) -> None:
        self._cfg = _FakePolicyConfig(cloud_ai_allowed=cloud_ai_allowed)

    def get_for_tenant(self, tenant_id: str) -> Any:
        return self._cfg


def _make_file(mime: str = "application/pdf", name: str = "doc.pdf") -> IntakeFile:
    return IntakeFile(
        file_id=uuid4(),
        file_path=f"/virtual/{name}",
        file_name=name,
        mime_type=mime,
        size_bytes=1024,
        sha256=hashlib.sha256(name.encode()).hexdigest(),
    )


def _make_package(files: list[IntakeFile]) -> IntakePackage:
    return IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_unit",
        files=files,
    )


@pytest.fixture
def service() -> DocumentExtractorService:
    return DocumentExtractorService(
        session_factory=None,  # type: ignore[arg-type]
        config=DocumentExtractorConfig(upload_dir="./data/test_uploads"),
    )


# --- Happy path ------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_single_pdf(service: DocumentExtractorService) -> None:
    pkg = _make_package([_make_file()])
    parser = FakeParser(text="parsed body")

    results = await service.extract_from_package(pkg, parser=parser)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ExtractionResult)
    assert r.package_id == pkg.package_id
    assert r.file_id == pkg.files[0].file_id
    assert r.tenant_id == "tenant_unit"
    assert r.parser_used == "docling_standard"
    assert r.extracted_text == "parsed body"
    assert r.structured_fields.get("page_count") == 1
    assert r.confidence == 1.0
    assert parser.calls == [(pkg.package_id, pkg.files[0].file_id)]


# --- Policy gate -----------------------------------------------------------


@pytest.mark.asyncio
async def test_policy_blocks_cloud_only_mime(service: DocumentExtractorService) -> None:
    # video/mp4 is NOT in DoclingStandardParser._SUPPORTED_MIMES — requires cloud.
    file = _make_file(mime="video/mp4", name="clip.mp4")
    pkg = _make_package([file])
    parser = FakeParser()
    policy = _FakePolicyEngine(cloud_ai_allowed=False)

    results = await service.extract_from_package(pkg, policy_engine=policy, parser=parser)

    assert len(results) == 1
    r = results[0]
    assert r.parser_used == "skipped_policy"
    assert r.extracted_text == ""
    assert r.confidence == 0.0
    assert r.structured_fields["skip_reason"] == "cloud_ai_disallowed_for_mime"
    # parser must NOT have been invoked
    assert parser.calls == []


@pytest.mark.asyncio
async def test_policy_allows_cloud_mime_when_enabled(
    service: DocumentExtractorService,
) -> None:
    file = _make_file(mime="video/mp4", name="clip.mp4")
    pkg = _make_package([file])
    parser = FakeParser(text="vid parsed")
    policy = _FakePolicyEngine(cloud_ai_allowed=True)

    results = await service.extract_from_package(pkg, policy_engine=policy, parser=parser)

    assert results[0].parser_used == "docling_standard"
    assert results[0].extracted_text == "vid parsed"


# --- Multi-file batch ------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_file_batch(service: DocumentExtractorService) -> None:
    files = [
        _make_file(name="a.pdf"),
        _make_file(name="b.pdf"),
        _make_file(name="c.pdf"),
    ]
    pkg = _make_package(files)
    parser = FakeParser()

    results = await service.extract_from_package(pkg, parser=parser)

    assert len(results) == 3
    assert {r.file_id for r in results} == {f.file_id for f in files}
    assert all(r.parser_used == "docling_standard" for r in results)
    assert len(parser.calls) == 3


# --- Empty package --------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_package_raises_value_error(service: DocumentExtractorService) -> None:
    # IntakePackage requires at least file or description, so add a description.
    from aiflow.intake.package import IntakeDescription

    pkg = IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_unit",
        files=[],
        descriptions=[IntakeDescription(text="context only")],
    )
    with pytest.raises(ValueError, match="at least one file"):
        await service.extract_from_package(pkg, parser=FakeParser())


# --- Parser injection default ---------------------------------------------


# --- Router wiring (S95) ---------------------------------------------------


class _FakeRouter:
    """In-memory MultiSignalRouter stub driving a predetermined plan."""

    def __init__(self, plan: list[dict[str, Any]]) -> None:
        self._plan = list(plan)
        self.calls: list[tuple[UUID, UUID]] = []

    async def decide(self, package: IntakePackage, file: IntakeFile) -> Any:
        from aiflow.contracts.routing_decision import RoutingDecision

        self.calls.append((package.package_id, file.file_id))
        entry = self._plan.pop(0)
        return RoutingDecision(
            package_id=package.package_id,
            file_id=file.file_id,
            tenant_id=package.tenant_id,
            chosen_parser=entry["chosen_parser"],
            reason=entry.get("reason", "test"),
            signals=entry.get("signals", {}),
            fallback_chain=entry.get("fallback_chain", []),
        )


class _FakeUnstructuredParser(FakeParser):
    PROVIDER_NAME = "unstructured_fast"

    async def parse(self, file: IntakeFile, package_context: IntakePackage) -> ParserResult:
        self.calls.append((package_context.package_id, file.file_id))
        return ParserResult(
            file_id=file.file_id,
            parser_name="unstructured_fast",
            text="fast path parsed",
            markdown="fast path parsed",
            page_count=1,
        )


@pytest.mark.asyncio
async def test_extract_from_package_with_router_picks_unstructured(
    service: DocumentExtractorService,
) -> None:
    from aiflow.providers.registry import ProviderRegistry

    file = _make_file()
    pkg = _make_package([file])

    router = _FakeRouter([{"chosen_parser": "unstructured_fast", "reason": "fast_path"}])
    registry = ProviderRegistry()
    registry.register_parser("unstructured_fast", _FakeUnstructuredParser)

    docling_parser = FakeParser(text="docling output")
    results = await service.extract_from_package(
        pkg,
        parser=docling_parser,
        router=router,
        registry=registry,
    )

    assert len(results) == 1
    r = results[0]
    assert r.parser_used == "unstructured_fast"
    assert r.extracted_text == "fast path parsed"
    assert r.structured_fields["routing_reason"] == "fast_path"
    # Routed path must NOT have invoked the injected Docling parser.
    assert docling_parser.calls == []


@pytest.mark.asyncio
async def test_extract_from_package_with_router_policy_skip(
    service: DocumentExtractorService,
) -> None:
    file = _make_file(mime="video/mp4", name="clip.mp4")
    pkg = _make_package([file])

    router = _FakeRouter(
        [{"chosen_parser": "skipped_policy", "reason": "cloud_ai_disallowed_for_mime"}]
    )

    results = await service.extract_from_package(
        pkg,
        parser=FakeParser(),
        router=router,
    )

    assert results[0].parser_used == "skipped_policy"
    assert results[0].structured_fields["skip_reason"] == "cloud_ai_disallowed_for_mime"


@pytest.mark.asyncio
async def test_extract_from_package_with_router_uses_injected_parser_by_name(
    service: DocumentExtractorService,
) -> None:
    """Injected parser whose PROVIDER_NAME matches the decision is preferred."""
    file = _make_file()
    pkg = _make_package([file])

    router = _FakeRouter([{"chosen_parser": "docling_standard", "reason": "default"}])
    parser = FakeParser(text="injected output")  # PROVIDER_NAME="docling_standard"

    results = await service.extract_from_package(pkg, parser=parser, router=router)

    assert results[0].parser_used == "docling_standard"
    assert results[0].extracted_text == "injected output"
    assert parser.calls == [(pkg.package_id, file.file_id)]


# --- Default parser --------------------------------------------------------


@pytest.mark.asyncio
async def test_default_parser_is_docling_standard(
    service: DocumentExtractorService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without an injected parser, service builds DoclingStandardParser (no network).

    Uses a StubDocling that extends DoclingStandardParser so the MIME-capability
    class method (``supports_mime``) remains available to the policy gate.
    """
    from aiflow.providers.parsers import docling_standard

    class StubDocling(docling_standard.DoclingStandardParser):
        async def parse(self, file: IntakeFile, package_context: IntakePackage) -> ParserResult:
            return ParserResult(
                file_id=file.file_id,
                parser_name="docling_standard",
                text="default path",
                markdown="default path",
                page_count=1,
            )

    monkeypatch.setattr(docling_standard, "DoclingStandardParser", StubDocling)

    # Clear any cached parser from a previous test.
    if hasattr(service, "_cached_default_parser"):
        delattr(service, "_cached_default_parser")

    pkg = _make_package([_make_file()])
    results = await service.extract_from_package(pkg)
    assert results[0].extracted_text == "default path"
