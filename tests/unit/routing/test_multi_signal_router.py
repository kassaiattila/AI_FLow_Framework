"""MultiSignalRouter — unit tests for S95 rule set.

@test_registry
suite: unit_routing
tags: [unit, routing, phase_1_5_sprint_i, s95]
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

import pytest

from aiflow.contracts.routing_decision import RoutingDecision
from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.providers.registry import ProviderRegistry
from aiflow.routing.router import (
    AZURE_DOCUMENT_INTELLIGENCE_PARSER,
    DOCLING_STANDARD_PARSER,
    SKIPPED_POLICY,
    UNSTRUCTURED_FAST_PARSER,
    MultiSignalRouter,
)


class _FakePolicyConfig:
    def __init__(self, cloud_ai_allowed: bool = False) -> None:
        self.cloud_ai_allowed = cloud_ai_allowed


class _FakePolicyEngine:
    def __init__(self, cloud_ai_allowed: bool = False) -> None:
        self._cfg = _FakePolicyConfig(cloud_ai_allowed=cloud_ai_allowed)

    def get_for_tenant(self, tenant_id: str) -> Any:
        return self._cfg


def _make_file(
    mime: str = "application/pdf",
    size: int = 1024,
    name: str = "doc.pdf",
    page_count: int | None = None,
) -> IntakeFile:
    source_metadata: dict[str, Any] = {}
    if page_count is not None:
        source_metadata["page_count"] = page_count
    return IntakeFile(
        file_id=uuid4(),
        file_path=f"/virtual/{name}",
        file_name=name,
        mime_type=mime,
        size_bytes=size,
        sha256=hashlib.sha256(name.encode()).hexdigest(),
        source_metadata=source_metadata,
    )


def _make_package(file: IntakeFile) -> IntakePackage:
    return IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_unit",
        files=[file],
    )


def _router(cloud_ai_allowed: bool = False) -> MultiSignalRouter:
    return MultiSignalRouter(
        policy_engine=_FakePolicyEngine(cloud_ai_allowed=cloud_ai_allowed),
        registry=ProviderRegistry(),
    )


@pytest.mark.asyncio
async def test_small_born_digital_pdf_goes_to_unstructured_fast() -> None:
    f = _make_file(mime="application/pdf", size=512_000)
    pkg = _make_package(f)
    d = await _router().decide(pkg, f)

    assert isinstance(d, RoutingDecision)
    assert d.chosen_parser == UNSTRUCTURED_FAST_PARSER
    assert d.fallback_chain == [DOCLING_STANDARD_PARSER]
    assert d.reason == "small_born_digital_text_fast_path"
    assert d.signals["size_bytes"] == 512_000
    assert d.signals["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_large_pdf_routed_to_docling_standard() -> None:
    f = _make_file(mime="application/pdf", size=6_000_000)
    pkg = _make_package(f)
    d = await _router().decide(pkg, f)

    assert d.chosen_parser == DOCLING_STANDARD_PARSER
    assert d.fallback_chain == []
    assert d.reason == "size_exceeds_fast_path_threshold"


@pytest.mark.asyncio
async def test_small_docx_goes_to_unstructured_fast() -> None:
    f = _make_file(
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=2_000_000,
        name="note.docx",
    )
    pkg = _make_package(f)
    d = await _router().decide(pkg, f)

    assert d.chosen_parser == UNSTRUCTURED_FAST_PARSER
    assert d.fallback_chain == [DOCLING_STANDARD_PARSER]


@pytest.mark.asyncio
async def test_video_with_cloud_disallowed_is_skipped() -> None:
    f = _make_file(mime="video/mp4", size=10_000, name="clip.mp4")
    pkg = _make_package(f)
    d = await _router(cloud_ai_allowed=False).decide(pkg, f)

    assert d.chosen_parser == SKIPPED_POLICY
    assert d.reason == "cloud_ai_disallowed_for_mime"
    assert d.fallback_chain == []


@pytest.mark.asyncio
async def test_png_scan_with_cloud_disallowed_goes_to_docling() -> None:
    """Docling handles images locally — no cloud needed, no policy skip."""
    f = _make_file(mime="image/png", size=800_000, name="scan.png")
    pkg = _make_package(f)
    d = await _router(cloud_ai_allowed=False).decide(pkg, f)

    assert d.chosen_parser == DOCLING_STANDARD_PARSER
    assert d.reason == "image_requires_docling_ocr"


@pytest.mark.asyncio
async def test_video_with_cloud_allowed_still_goes_to_docling_not_skipped() -> None:
    """cloud_ai_allowed=True lifts the policy gate — fall through to Rule 2."""
    f = _make_file(mime="video/mp4", size=10_000, name="clip.mp4")
    pkg = _make_package(f)
    d = await _router(cloud_ai_allowed=True).decide(pkg, f)

    assert d.chosen_parser == DOCLING_STANDARD_PARSER
    assert d.reason == "mime_outside_fast_path_set"


@pytest.mark.asyncio
async def test_exact_5mb_pdf_takes_fast_path_boundary() -> None:
    """5_000_000 bytes is inclusive — the <= boundary."""
    f = _make_file(mime="application/pdf", size=5_000_000)
    pkg = _make_package(f)
    d = await _router().decide(pkg, f)

    assert d.chosen_parser == UNSTRUCTURED_FAST_PARSER


@pytest.mark.asyncio
async def test_fallback_chain_content_check() -> None:
    """Fast-path decisions always carry docling_standard as sole fallback."""
    f = _make_file(mime="text/plain", size=10, name="a.txt")
    pkg = _make_package(f)
    d = await _router().decide(pkg, f)

    assert d.fallback_chain == [DOCLING_STANDARD_PARSER]
    assert d.chosen_parser == UNSTRUCTURED_FAST_PARSER


# --- S96: Rule 2.5 (Azure DI scan-aware routing) --------------------------


@pytest.mark.asyncio
async def test_scan_pdf_cloud_allowed_with_env_routes_to_azure_di(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scanned PDF hint + cloud allowed + endpoint present → Azure DI."""
    monkeypatch.setenv("AZURE_DOC_INTEL_ENDPOINT", "https://fake.cognitiveservices.azure.com/")
    f = _make_file(
        mime="application/pdf",
        size=20_000_000,
        name="scan.pdf",
        page_count=10,
    )
    pkg = _make_package(f)
    d = await _router(cloud_ai_allowed=True).decide(pkg, f)

    assert d.chosen_parser == AZURE_DOCUMENT_INTELLIGENCE_PARSER
    assert d.fallback_chain == [DOCLING_STANDARD_PARSER]
    assert d.reason == "scan_pdf_cloud_allowed_azure_di"
    assert d.signals["needs_ocr"] is True
    assert d.signals["azure_endpoint_present"] is True


@pytest.mark.asyncio
async def test_scan_pdf_cloud_disallowed_falls_back_to_docling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud disallowed keeps scans on local Docling — no policy skip."""
    monkeypatch.setenv("AZURE_DOC_INTEL_ENDPOINT", "https://fake.cognitiveservices.azure.com/")
    f = _make_file(
        mime="application/pdf",
        size=20_000_000,
        name="scan.pdf",
        page_count=10,
    )
    pkg = _make_package(f)
    d = await _router(cloud_ai_allowed=False).decide(pkg, f)

    assert d.chosen_parser == DOCLING_STANDARD_PARSER
    assert d.reason != "scan_pdf_cloud_allowed_azure_di"
    assert d.signals["needs_ocr"] is True


@pytest.mark.asyncio
async def test_scan_pdf_cloud_allowed_without_env_falls_back_to_docling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing AZURE_DOC_INTEL_ENDPOINT must NOT trip Rule 2.5."""
    monkeypatch.delenv("AZURE_DOC_INTEL_ENDPOINT", raising=False)
    f = _make_file(
        mime="application/pdf",
        size=20_000_000,
        name="scan.pdf",
        page_count=10,
    )
    pkg = _make_package(f)
    d = await _router(cloud_ai_allowed=True).decide(pkg, f)

    assert d.chosen_parser == DOCLING_STANDARD_PARSER
    assert d.signals["azure_endpoint_present"] is False
    assert d.signals["needs_ocr"] is True
