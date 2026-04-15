"""DocumentExtractorService.extract() shim regression.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, compat, document_extractor, regression]

Pins the v1.3 → v1.4 extract() shim contract beyond the happy path covered by
test_backward_compat_extract_file.py. Guards against regressions where:
- The DeprecationWarning category, filterability, or stacklevel drift.
- The warning message loses the "extract_from_package" migration hint.
- Pre-flight validation on file_path is skipped before the warning fires.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from aiflow.services.document_extractor.service import (
    DocumentExtractorConfig,
    DocumentExtractorService,
)


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "sample.pdf"
    p.write_bytes(b"%PDF-1.4\n%shim regression\n")
    return p


@pytest.fixture
def extractor_service() -> DocumentExtractorService:
    return DocumentExtractorService(
        session_factory=None,  # type: ignore[arg-type]
        config=DocumentExtractorConfig(upload_dir="./data/test_uploads"),
    )


class TestDeprecationWarningCategory:
    @pytest.mark.asyncio
    async def test_warning_is_deprecation_warning_subclass(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with pytest.raises(Exception):
                await extractor_service.extract(sample_pdf)

        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        assert deprecations, "extract() must emit at least one DeprecationWarning"

    @pytest.mark.asyncio
    async def test_warning_message_mentions_migration_target(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with pytest.raises(Exception):
                await extractor_service.extract(sample_pdf)

        messages = [str(w.message) for w in captured if issubclass(w.category, DeprecationWarning)]
        assert any("extract_from_package" in m for m in messages), (
            "Deprecation message must point at the v1.4 replacement API"
        )

    @pytest.mark.asyncio
    async def test_warning_message_mentions_version(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with pytest.raises(Exception):
                await extractor_service.extract(sample_pdf)

        messages = [str(w.message) for w in captured if issubclass(w.category, DeprecationWarning)]
        assert any("1.4" in m or "v1.4" in m for m in messages), (
            "Deprecation message must cite the version where the shim was introduced"
        )


class TestDeprecationFilterable:
    """Downstream callers must be able to silence the shim warning cleanly."""

    @pytest.mark.asyncio
    async def test_simplefilter_ignore_suppresses_warning(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(Exception):
                await extractor_service.extract(sample_pdf)

        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        assert not deprecations, (
            "`simplefilter('ignore', DeprecationWarning)` must suppress the shim warning"
        )

    @pytest.mark.asyncio
    async def test_filterwarnings_message_regex_suppresses_warning(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            warnings.filterwarnings(
                "ignore",
                category=DeprecationWarning,
                message=r"extract\(file_path\).*",
            )
            with pytest.raises(Exception):
                await extractor_service.extract(sample_pdf)

        shim_warnings = [
            w
            for w in captured
            if issubclass(w.category, DeprecationWarning) and "extract(file_path)" in str(w.message)
        ]
        assert not shim_warnings, (
            "Message-regex filter on 'extract(file_path)' must suppress the shim warning"
        )


class TestValidationBeforeWarning:
    """ValueError on bad input must still fire even when the warning is silenced."""

    @pytest.mark.asyncio
    async def test_empty_path_raises_value_error(
        self, extractor_service: DocumentExtractorService
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(ValueError, match="file_path is required"):
                await extractor_service.extract("")

    @pytest.mark.asyncio
    async def test_dot_path_raises_value_error(
        self, extractor_service: DocumentExtractorService
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(ValueError, match="file_path is required"):
                await extractor_service.extract(".")

    @pytest.mark.asyncio
    async def test_missing_file_raises_value_error(
        self, extractor_service: DocumentExtractorService, tmp_path: Path
    ) -> None:
        missing = tmp_path / "no_such_file.pdf"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(ValueError, match="does not exist"):
                await extractor_service.extract(missing)

    @pytest.mark.asyncio
    async def test_directory_raises_value_error(
        self, extractor_service: DocumentExtractorService, tmp_path: Path
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(ValueError, match="is not a file"):
                await extractor_service.extract(tmp_path)


class TestShimDelegatesConsistentlyOnPathTypes:
    """str and Path inputs must both reach the pre-flight checks identically."""

    @pytest.mark.asyncio
    async def test_str_path_accepted_until_db(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(Exception) as excinfo:
                await extractor_service.extract(str(sample_pdf))
        assert not isinstance(excinfo.value, ValueError), (
            "str path to existing file must not fail pre-flight validation"
        )

    @pytest.mark.asyncio
    async def test_path_object_accepted_until_db(
        self, extractor_service: DocumentExtractorService, sample_pdf: Path
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(Exception) as excinfo:
                await extractor_service.extract(sample_pdf)
        assert not isinstance(excinfo.value, ValueError), (
            "Path object to existing file must not fail pre-flight validation"
        )
