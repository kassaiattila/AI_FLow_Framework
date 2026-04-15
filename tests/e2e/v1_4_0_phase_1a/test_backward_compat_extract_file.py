"""Backward compat extract(file) E2E — DeprecationWarning shim contract.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, compat, document_extractor]

Validates the v1.3 → v1.4 shim in DocumentExtractorService:
- extract(file_path) emits DeprecationWarning
- _build_single_file_package() produces a valid IntakePackage from a real file
- extract_from_package() raises NotImplementedError in Phase 1a
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

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


class TestExtractFromPackageNotImplemented:
    @pytest.mark.asyncio
    async def test_raises_not_implemented(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        pkg = extractor_service._build_single_file_package(sample_pdf)
        with pytest.raises(NotImplementedError, match="Phase 1a"):
            await extractor_service.extract_from_package(pkg)

    @pytest.mark.asyncio
    async def test_not_implemented_message_mentions_phase_1c(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        pkg = extractor_service._build_single_file_package(sample_pdf)
        with pytest.raises(NotImplementedError) as excinfo:
            await extractor_service.extract_from_package(pkg)
        assert "Phase 1c" in str(excinfo.value) or "skeleton" in str(excinfo.value)


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
