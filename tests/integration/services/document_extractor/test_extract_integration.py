"""DocumentExtractorService.extract_from_package() — real-services integration.

@test_registry
suite: integration_services_document_extractor
tags: [integration, services, document_extractor, sprint_i, phase_1_5, real]

Real Docling + real PolicyEngine (YAML profile). Postgres is NOT required by
S94 scope because extract_from_package() does not persist — DB wiring lands
in S97. Docker postgres stays optional here.

Skip conditions
---------------
- ``tests/fixtures/sample_invoice.pdf`` absent → skip.

The fixture is intentionally NOT committed; session prompt STOP rule
forbids synthesising one. To run this test locally, drop any small
PDF into ``tests/fixtures/sample_invoice.pdf``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.contracts.extraction_result import ExtractionResult
from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine
from aiflow.services.document_extractor.service import (
    DocumentExtractorConfig,
    DocumentExtractorService,
)

SAMPLE_PDF = Path(__file__).resolve().parents[3] / "fixtures" / "sample_invoice.pdf"

pytestmark = pytest.mark.skipif(
    not SAMPLE_PDF.is_file(),
    reason=(
        f"sample invoice fixture missing at {SAMPLE_PDF}. "
        "Drop any small PDF there to enable the real-Docling integration test."
    ),
)


@pytest.fixture
def service() -> DocumentExtractorService:
    return DocumentExtractorService(
        session_factory=None,  # type: ignore[arg-type]
        config=DocumentExtractorConfig(upload_dir="./data/test_uploads"),
    )


@pytest.fixture
def real_policy_engine() -> PolicyEngine:
    """PolicyEngine with on-prem defaults — cloud_ai_allowed=False."""
    return PolicyEngine(profile_config=PolicyConfig())


def _file_from_disk(path: Path) -> IntakeFile:
    data = path.read_bytes()
    return IntakeFile(
        file_id=uuid4(),
        file_path=str(path),
        file_name=path.name,
        mime_type="application/pdf",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_real_docling_pipeline_produces_text(
    service: DocumentExtractorService,
    real_policy_engine: PolicyEngine,
) -> None:
    file = _file_from_disk(SAMPLE_PDF)
    pkg = IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id=os.environ.get("AIFLOW_TEST_TENANT", "integration_tenant"),
        files=[file],
    )

    results = await service.extract_from_package(pkg, policy_engine=real_policy_engine)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ExtractionResult)
    assert r.parser_used == "docling_standard"
    assert r.extracted_text.strip(), "Docling standard pipeline returned empty text"
    assert r.file_id == file.file_id
    assert r.package_id == pkg.package_id


@pytest.mark.asyncio
@pytest.mark.slow
async def test_policy_skips_unknown_mime(
    service: DocumentExtractorService,
    real_policy_engine: PolicyEngine,
) -> None:
    """Unknown-to-Docling MIME + cloud_ai_allowed=False → parser_used=skipped_policy."""
    data = SAMPLE_PDF.read_bytes()
    file = IntakeFile(
        file_id=uuid4(),
        file_path=str(SAMPLE_PDF),
        file_name="clip.mp4",
        mime_type="video/mp4",  # not in DoclingStandardParser._SUPPORTED_MIMES
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    pkg = IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="integration_tenant",
        files=[file],
    )

    results = await service.extract_from_package(pkg, policy_engine=real_policy_engine)

    assert results[0].parser_used == "skipped_policy"
    assert results[0].structured_fields["skip_reason"] == "cloud_ai_disallowed_for_mime"
