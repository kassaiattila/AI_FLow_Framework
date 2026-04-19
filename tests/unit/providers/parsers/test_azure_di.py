"""AzureDocumentIntelligenceParser — unit tests.

These tests never touch Azure. The SDK is monkeypatched via a fake module
injected into ``sys.modules`` so the provider's lazy ``from azure...``
import inside ``_do_parse`` resolves to our stub.

@test_registry
suite: unit_providers
tags: [unit, providers, phase_1_5_sprint_i, s96]
"""

from __future__ import annotations

import hashlib
import sys
import types
from typing import Any
from uuid import uuid4

import pytest

from aiflow.contracts.parser_result import ParserResult
from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.providers.parsers.azure_document_intelligence import (
    AzureDIConfig,
    AzureDocumentIntelligenceParser,
)


def _make_file(
    mime: str = "application/pdf",
    size: int = 2_000_000,
    name: str = "scan.pdf",
    tmp_path: Any = None,
) -> IntakeFile:
    path = str(tmp_path / name) if tmp_path is not None else f"/virtual/{name}"
    if tmp_path is not None:
        (tmp_path / name).write_bytes(b"%PDF-1.4 minimal stub")
    return IntakeFile(
        file_id=uuid4(),
        file_path=path,
        file_name=name,
        mime_type=mime,
        size_bytes=size,
        sha256=hashlib.sha256(name.encode()).hexdigest(),
    )


def _make_package(file: IntakeFile) -> IntakePackage:
    return IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_unit",
        files=[file],
    )


def test_supports_mime_covers_pdf_and_images() -> None:
    assert AzureDocumentIntelligenceParser.supports_mime("application/pdf")
    assert AzureDocumentIntelligenceParser.supports_mime("image/png")
    assert AzureDocumentIntelligenceParser.supports_mime("image/jpeg")
    assert AzureDocumentIntelligenceParser.supports_mime("image/tiff")
    assert not AzureDocumentIntelligenceParser.supports_mime("text/plain")
    assert not AzureDocumentIntelligenceParser.supports_mime(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@pytest.mark.asyncio
async def test_estimate_cost_scales_with_size() -> None:
    parser = AzureDocumentIntelligenceParser(config=AzureDIConfig())
    small = _make_file(size=50_000)
    medium = _make_file(size=500_000)
    large = _make_file(size=5_000_000)

    cost_small = await parser.estimate_cost(small)
    cost_medium = await parser.estimate_cost(medium)
    cost_large = await parser.estimate_cost(large)

    assert cost_small == pytest.approx(0.001)
    assert cost_medium == pytest.approx(0.005)
    assert cost_large == pytest.approx(0.050)
    assert cost_large > cost_medium > cost_small > 0.0


@pytest.mark.asyncio
async def test_parse_maps_sdk_response_to_parser_result(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end parse flow with a fake SDK — no cloud calls."""

    class _FakeCell:
        def __init__(self, row: int, col: int, content: str) -> None:
            self.row_index = row
            self.column_index = col
            self.content = content

    class _FakeBoundingRegion:
        def __init__(self, page: int) -> None:
            self.page_number = page

    class _FakeCaption:
        def __init__(self, content: str) -> None:
            self.content = content

    class _FakeTable:
        def __init__(self) -> None:
            self.row_count = 2
            self.column_count = 2
            self.cells = [
                _FakeCell(0, 0, "Header1"),
                _FakeCell(0, 1, "Header2"),
                _FakeCell(1, 0, "v1"),
                _FakeCell(1, 1, "v2"),
            ]
            self.caption = _FakeCaption("Invoice line items")
            self.bounding_regions = [_FakeBoundingRegion(page=1)]

    class _FakePage:
        pass

    class _FakeResult:
        def __init__(self) -> None:
            self.content = "Hello world"
            self.pages = [_FakePage(), _FakePage()]
            self.tables = [_FakeTable()]

    class _FakePoller:
        def result(self, timeout: int) -> _FakeResult:
            assert timeout > 0
            return _FakeResult()

    class _FakeClient:
        def __init__(self, endpoint: str, credential: Any) -> None:
            self._endpoint = endpoint
            self._credential = credential

        def begin_analyze_document(self, model_id: str, body: Any) -> _FakePoller:
            assert model_id == "prebuilt-layout"
            assert body.read()
            return _FakePoller()

    class _FakeCred:
        def __init__(self, key: str) -> None:
            self.key = key

    fake_di = types.ModuleType("azure.ai.documentintelligence")
    fake_di.DocumentIntelligenceClient = _FakeClient
    fake_creds = types.ModuleType("azure.core.credentials")
    fake_creds.AzureKeyCredential = _FakeCred
    monkeypatch.setitem(sys.modules, "azure.ai.documentintelligence", fake_di)
    monkeypatch.setitem(sys.modules, "azure.core.credentials", fake_creds)

    monkeypatch.setenv("AZURE_DOC_INTEL_ENDPOINT", "https://fake.azure.test/")
    monkeypatch.setenv("AZURE_DOC_INTEL_KEY", "dummy-key")

    parser = AzureDocumentIntelligenceParser(config=AzureDIConfig.from_env())
    file = _make_file(tmp_path=tmp_path)
    package = _make_package(file)

    result = await parser.parse(file, package)

    assert isinstance(result, ParserResult)
    assert result.parser_name == AzureDocumentIntelligenceParser.PROVIDER_NAME
    assert result.text == "Hello world"
    assert result.page_count == 2
    assert len(result.tables) == 1
    table = result.tables[0]
    assert table["caption"] == "Invoice line items"
    assert table["page_number"] == 1
    assert "Header1" in table["markdown"]
    assert "v2" in table["markdown"]
    assert result.metadata["model_id"] == "prebuilt-layout"
    assert result.metadata["tenant_id"] == "tenant_unit"


@pytest.mark.asyncio
async def test_parse_without_endpoint_raises(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AZURE_DOC_INTEL_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_DOC_INTEL_KEY", raising=False)
    parser = AzureDocumentIntelligenceParser(config=AzureDIConfig())
    file = _make_file(tmp_path=tmp_path)
    package = _make_package(file)

    with pytest.raises(RuntimeError, match="AZURE_DOC_INTEL_ENDPOINT"):
        await parser.parse(file, package)
