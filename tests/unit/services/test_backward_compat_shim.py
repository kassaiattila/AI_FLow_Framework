"""
@test_registry:
    suite: service-unit
    component: services.document_extractor.backward_compat
    covers: [src/aiflow/services/document_extractor/service.py]
    phase: D0.7
    priority: high
    estimated_duration_ms: 300
    requires_services: []
    tags: [service, document-extractor, backward-compat, shim, deprecation]
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.document_extractor.service import (
    DocumentExtractorService,
)


@pytest.fixture()
def service() -> DocumentExtractorService:
    session_factory = AsyncMock()
    return DocumentExtractorService(session_factory=session_factory)


@pytest.fixture()
def tmp_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.pdf"
    f.write_bytes(b"%PDF-1.4 fake pdf content for testing purposes only")
    return f


class TestExtractDeprecationWarning:
    """extract() must issue DeprecationWarning while keeping full functionality."""

    @pytest.mark.asyncio
    async def test_extract_issues_deprecation_warning(
        self, service: DocumentExtractorService, tmp_file: Path
    ) -> None:
        service.get_config = AsyncMock(
            return_value=MagicMock(
                parser="docling",
                extraction_model="openai/gpt-4o",
                fields=[],
                validation_rules=[],
                document_type="invoice",
                customer="default",
            )
        )
        service._parse_document = AsyncMock(
            return_value={"text": "hello", "markdown": "hello", "parser_used": "docling"}
        )
        service._extract_fields = AsyncMock(return_value={"_confidence": 0.9})
        service._validate_fields = MagicMock(return_value=[])
        service._store_result = AsyncMock(return_value="db-001")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = await service.extract(tmp_file, config_name="invoice-hu")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated in v1.4.0" in str(w[0].message)
            assert "extract_from_package" in str(w[0].message)

        assert result.source_file == tmp_file.name

    @pytest.mark.asyncio
    async def test_extract_signature_unchanged(self, service: DocumentExtractorService) -> None:
        """extract() signature must accept (file_path, config_name) — backward compat."""
        import inspect

        sig = inspect.signature(service.extract)
        params = list(sig.parameters.keys())
        assert params == ["file_path", "config_name"]
        assert sig.parameters["file_path"].annotation == "str | Path"
        assert sig.parameters["config_name"].annotation == "str | None"
        assert sig.parameters["config_name"].default is None

    @pytest.mark.asyncio
    async def test_extract_still_returns_extraction_result(
        self, service: DocumentExtractorService, tmp_file: Path
    ) -> None:
        service.get_config = AsyncMock(
            return_value=MagicMock(
                parser="docling",
                extraction_model="openai/gpt-4o",
                fields=[],
                validation_rules=[],
                document_type="invoice",
                customer="default",
            )
        )
        service._parse_document = AsyncMock(
            return_value={"text": "content", "markdown": "# content", "parser_used": "fallback"}
        )
        service._extract_fields = AsyncMock(
            return_value={"vendor_name": "Acme", "_confidence": 0.8}
        )
        service._validate_fields = MagicMock(return_value=[])
        service._store_result = AsyncMock(return_value="db-002")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await service.extract(tmp_file, config_name="invoice-hu")

        assert result.config_name == "invoice-hu"
        assert result.extracted_fields["vendor_name"] == "Acme"
        assert result.confidence == 0.8


class TestExtractFromPackage:
    """extract_from_package() must raise NotImplementedError in Phase 1a."""

    @pytest.mark.asyncio
    async def test_extract_from_package_raises_not_implemented(
        self, service: DocumentExtractorService, tmp_file: Path
    ) -> None:
        package = service._build_single_file_package(tmp_file, tenant_id="test-tenant")
        with pytest.raises(NotImplementedError, match="Phase 1a skeleton"):
            await service.extract_from_package(package, config_name="invoice-hu")

    @pytest.mark.asyncio
    async def test_extract_from_package_accepts_package_and_config_name(
        self, service: DocumentExtractorService
    ) -> None:
        import inspect

        sig = inspect.signature(service.extract_from_package)
        params = list(sig.parameters.keys())
        assert "package" in params
        assert "config_name" in params


class TestBuildSingleFilePackage:
    """_build_single_file_package() must create a valid IntakePackage."""

    def test_creates_valid_intake_package(
        self, service: DocumentExtractorService, tmp_file: Path
    ) -> None:
        from aiflow.intake.package import IntakePackage, IntakeSourceType

        package = service._build_single_file_package(tmp_file)
        assert isinstance(package, IntakePackage)
        assert package.source_type == IntakeSourceType.FILE_UPLOAD
        assert package.tenant_id == "default"
        assert len(package.files) == 1

    def test_file_metadata_correct(self, service: DocumentExtractorService, tmp_file: Path) -> None:
        package = service._build_single_file_package(tmp_file, tenant_id="acme")
        f = package.files[0]
        assert f.file_name == tmp_file.name
        assert f.file_path == str(tmp_file)
        assert f.size_bytes == tmp_file.stat().st_size
        assert len(f.sha256) == 64
        assert f.mime_type  # non-empty

    def test_custom_tenant_id(self, service: DocumentExtractorService, tmp_file: Path) -> None:
        package = service._build_single_file_package(tmp_file, tenant_id="custom-tenant")
        assert package.tenant_id == "custom-tenant"

    def test_sha256_is_deterministic(
        self, service: DocumentExtractorService, tmp_file: Path
    ) -> None:
        p1 = service._build_single_file_package(tmp_file)
        p2 = service._build_single_file_package(tmp_file)
        assert p1.files[0].sha256 == p2.files[0].sha256
