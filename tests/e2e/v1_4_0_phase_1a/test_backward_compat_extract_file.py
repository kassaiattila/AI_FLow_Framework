"""Backward compat extract(file) E2E — DeprecationWarning shim contract.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, compat, document_extractor]

Validates the v1.3 → v1.4 shim in DocumentExtractorService:
- extract(file_path) emits DeprecationWarning
- _build_single_file_package() produces a valid IntakePackage from a real file
- extract_from_package() returns a list of ExtractionResult (Sprint I S94 onwards)
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from aiflow.contracts.extraction_result import ExtractionResult as PackageExtractionResult
from aiflow.intake.package import IntakePackage, IntakeSourceType
from aiflow.services.document_extractor.service import (
    DocumentExtractorConfig,
    DocumentExtractorService,
)


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a tiny real file on disk for sha256/stat() checks."""
    p = tmp_path / "sample.pdf"
    p.write_bytes(b"%PDF-1.4\n%test content\n")
    return p


@pytest.fixture
def extractor_service() -> DocumentExtractorService:
    """Construct the service with a sentinel session_factory (shim methods don't hit DB)."""
    return DocumentExtractorService(
        session_factory=None,  # type: ignore[arg-type]
        config=DocumentExtractorConfig(upload_dir="./data/test_uploads"),
    )


class TestBuildSingleFilePackage:
    def test_returns_valid_intake_package(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        pkg = extractor_service._build_single_file_package(sample_pdf, tenant_id="tenant_x")
        assert isinstance(pkg, IntakePackage)
        assert pkg.tenant_id == "tenant_x"
        assert pkg.source_type == IntakeSourceType.FILE_UPLOAD
        assert len(pkg.files) == 1

    def test_file_metadata_populated(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        pkg = extractor_service._build_single_file_package(sample_pdf)
        f = pkg.files[0]
        assert f.file_name == "sample.pdf"
        assert f.size_bytes == sample_pdf.stat().st_size
        assert len(f.sha256) == 64
        assert all(c in "0123456789abcdef" for c in f.sha256)
        assert f.mime_type in ("application/pdf", "application/octet-stream")

    def test_default_tenant_fallback(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        pkg = extractor_service._build_single_file_package(sample_pdf)
        assert pkg.tenant_id == "default"

    def test_package_status_is_received(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        from aiflow.intake.package import IntakePackageStatus

        pkg = extractor_service._build_single_file_package(sample_pdf)
        assert pkg.status == IntakePackageStatus.RECEIVED


class TestExtractFromPackageReturnsResults:
    """Sprint I S94 (v1.4.5.1): extract_from_package() is no longer a stub.

    The body lives in DocumentExtractorService.extract_from_package() and
    delegates per-file parsing to a ParserProvider. These tests exercise the
    DB-less path with an injected in-memory ParserProvider so the assertion
    is on the contract shape, not on Docling output.
    """

    @pytest.mark.asyncio
    async def test_returns_list_of_extraction_results(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        from uuid import uuid4

        from aiflow.contracts.parser_result import ParserResult
        from aiflow.intake.package import IntakeFile
        from aiflow.providers.interfaces import ParserProvider
        from aiflow.providers.metadata import ProviderMetadata

        class _StubParser(ParserProvider):
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
                return ParserResult(
                    file_id=file.file_id,
                    parser_name="docling_standard",
                    text="stub parsed text",
                    markdown="stub parsed text",
                    page_count=1,
                )

            async def health_check(self) -> bool:
                return True

            async def estimate_cost(self, file: IntakeFile) -> float:
                return 0.0

        _ = uuid4  # silence lint for unused import
        pkg = extractor_service._build_single_file_package(sample_pdf)
        results = await extractor_service.extract_from_package(pkg, parser=_StubParser())

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], PackageExtractionResult)
        assert results[0].parser_used == "docling_standard"
        assert results[0].extracted_text == "stub parsed text"
        assert results[0].file_id == pkg.files[0].file_id


class TestDeprecationShim:
    @pytest.mark.asyncio
    async def test_extract_emits_deprecation_warning(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        # Expect the DeprecationWarning to fire before any DB/parse work hits.
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with pytest.raises(Exception):  # downstream fails (no DB/parser) — not the point
                await extractor_service.extract(sample_pdf)

        assert any(
            issubclass(w.category, DeprecationWarning) and "extract_from_package" in str(w.message)
            for w in captured
        )

    @pytest.mark.asyncio
    async def test_extract_rejects_empty_path(
        self, extractor_service: DocumentExtractorService
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(ValueError, match="file_path is required"):
                await extractor_service.extract("")

    @pytest.mark.asyncio
    async def test_extract_rejects_missing_file(
        self, extractor_service: DocumentExtractorService, tmp_path: Path
    ) -> None:
        missing = tmp_path / "does_not_exist.pdf"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(ValueError, match="does not exist"):
                await extractor_service.extract(missing)
