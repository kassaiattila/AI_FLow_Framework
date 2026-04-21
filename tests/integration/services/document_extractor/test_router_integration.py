"""MultiSignalRouter + real providers — integration test.

@test_registry
suite: integration_services_document_extractor
tags: [integration, services, document_extractor, routing, sprint_i, phase_1_5, s95, real]

Real PolicyEngine + real ProviderRegistry + real DoclingStandardParser +
real UnstructuredParser. Fixtures are gated: if ``tests/fixtures/`` does not
contain a small PDF (``sample_pdf_small.pdf``) the whole module is skipped.
Per user preference (2026-04-19) real invoices from
``data/uploads/invoices/`` must NEVER be copied into the repo — drop any
suitable small PDF manually to enable the test.

Additionally skipped when the ``unstructured`` Python package fails to
import (known S95 venv segfault on Windows; see session follow-up).
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest


def _unstructured_importable() -> bool:
    """Probe ``unstructured.partition.auto`` in a subprocess.

    ``pytest.importorskip`` cannot catch segfaults — the known S95 venv
    crash during ``unstructured.partition.auto`` import kills the whole
    collector otherwise. An isolated subprocess safely surfaces it as a
    non-zero exit.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from unstructured.partition.auto import partition"],
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


_UNSTRUCTURED_OK = _unstructured_importable()

from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType  # noqa: E402
from aiflow.policy import PolicyConfig  # noqa: E402
from aiflow.policy.engine import PolicyEngine  # noqa: E402
from aiflow.providers.parsers import (  # noqa: E402
    DoclingStandardParser,
    UnstructuredParser,
    register_default_parsers,
)
from aiflow.providers.registry import ProviderRegistry  # noqa: E402
from aiflow.routing.router import MultiSignalRouter  # noqa: E402
from aiflow.services.document_extractor.service import (  # noqa: E402
    DocumentExtractorConfig,
    DocumentExtractorService,
)

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
SMALL_PDF = FIXTURES / "sample_pdf_small.pdf"

pytestmark = [
    pytest.mark.skipif(
        not SMALL_PDF.is_file(),
        reason=(
            f"sample_pdf_small.pdf missing at {SMALL_PDF}. "
            "Drop any born-digital PDF <=5MB there to enable the S95 router test."
        ),
    ),
    pytest.mark.skipif(
        not _UNSTRUCTURED_OK,
        reason=(
            "unstructured.partition.auto not importable (segfault or ImportError). "
            "Run a dep-triage session to restore the fast-path parser."
        ),
    ),
]


def _pkg_for(path: Path) -> tuple[IntakePackage, IntakeFile]:
    file = IntakeFile(
        file_id=uuid4(),
        file_path=str(path),
        file_name=path.name,
        mime_type="application/pdf",
        size_bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    pkg = IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_integ_s95",
        files=[file],
    )
    return pkg, file


@pytest.fixture
def policy_engine() -> PolicyEngine:
    return PolicyEngine(profile_config=PolicyConfig())


@pytest.fixture
def registry() -> ProviderRegistry:
    r = ProviderRegistry()
    register_default_parsers(r)
    return r


@pytest.fixture
def service() -> DocumentExtractorService:
    return DocumentExtractorService(
        session_factory=None,  # type: ignore[arg-type]
        config=DocumentExtractorConfig(upload_dir="./data/test_uploads"),
    )


@pytest.mark.asyncio
async def test_small_pdf_routes_to_unstructured(
    service: DocumentExtractorService,
    policy_engine: PolicyEngine,
    registry: ProviderRegistry,
) -> None:
    router = MultiSignalRouter(policy_engine=policy_engine, registry=registry)
    pkg, _ = _pkg_for(SMALL_PDF)

    results = await service.extract_from_package(
        pkg,
        policy_engine=policy_engine,
        router=router,
        registry=registry,
    )

    assert len(results) == 1
    r = results[0]
    assert r.parser_used == UnstructuredParser.PROVIDER_NAME
    assert r.extracted_text.strip() != ""
    assert r.structured_fields["routing_reason"] == "small_born_digital_text_fast_path"


@pytest.mark.asyncio
async def test_routing_decision_signals_match_file(
    service: DocumentExtractorService,
    policy_engine: PolicyEngine,
    registry: ProviderRegistry,
) -> None:
    """End-to-end router output carries the file's MIME + size."""
    router = MultiSignalRouter(policy_engine=policy_engine, registry=registry)
    pkg, file = _pkg_for(SMALL_PDF)

    decision = await router.decide(pkg, file)

    assert decision.signals["size_bytes"] == file.size_bytes
    assert decision.signals["mime_type"] == "application/pdf"
    assert decision.chosen_parser in {
        UnstructuredParser.PROVIDER_NAME,
        DoclingStandardParser.PROVIDER_NAME,
    }
