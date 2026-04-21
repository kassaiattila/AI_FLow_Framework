"""Profile A (cloud disallowed) — Azure DI must never be routed or resolved.

@test_registry
suite: integration_services_document_extractor
tags: [integration, services, document_extractor, routing, phase_1_5_sprint_i, s96, real]

Uses the real ``PolicyEngine`` + real ``ProviderRegistry`` + real
``register_default_parsers`` so the Azure DI parser class is in the
registry when the SDK extra is installed. A spy ``ProviderRegistry``
wrapper fails the test if any code path attempts to resolve
``azure_document_intelligence`` under Profile A (cloud_ai_allowed=False).
"""

from __future__ import annotations

import hashlib
import os
from uuid import uuid4

import pytest

from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine
from aiflow.providers.parsers import register_default_parsers
from aiflow.providers.registry import ProviderRegistry
from aiflow.routing.router import (
    AZURE_DOCUMENT_INTELLIGENCE_PARSER,
    DOCLING_STANDARD_PARSER,
    MultiSignalRouter,
)


class _SpyRegistry(ProviderRegistry):
    """Registry wrapper that records every parser name ever requested."""

    def __init__(self) -> None:
        super().__init__()
        self.resolution_log: list[str] = []

    def get_parser(self, name: str):  # type: ignore[override]
        self.resolution_log.append(name)
        return super().get_parser(name)


def _make_file(
    mime: str,
    size: int,
    name: str,
    page_count: int | None = None,
) -> IntakeFile:
    meta: dict[str, int] = {}
    if page_count is not None:
        meta["page_count"] = page_count
    return IntakeFile(
        file_id=uuid4(),
        file_path=f"/virtual/{name}",
        file_name=name,
        mime_type=mime,
        size_bytes=size,
        sha256=hashlib.sha256(name.encode()).hexdigest(),
        source_metadata=meta,
    )


def _make_package(files: list[IntakeFile]) -> IntakePackage:
    return IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="tenant_profile_a_integ",
        files=files,
    )


@pytest.fixture
def profile_a_engine() -> PolicyEngine:
    """Cloud-disallowed profile (on-prem Profile A)."""
    return PolicyEngine(profile_config=PolicyConfig(cloud_ai_allowed=False))


@pytest.fixture
def spy_registry() -> _SpyRegistry:
    registry = _SpyRegistry()
    register_default_parsers(registry)
    return registry


@pytest.mark.asyncio
async def test_profile_a_never_routes_any_file_to_azure_di(
    profile_a_engine: PolicyEngine,
    spy_registry: _SpyRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with the Azure env configured, Profile A must keep cloud off."""
    monkeypatch.setenv("AZURE_DOC_INTEL_ENDPOINT", "https://fake.azure.test/")
    monkeypatch.setenv("AZURE_DOC_INTEL_KEY", "dummy")

    router = MultiSignalRouter(policy_engine=profile_a_engine, registry=spy_registry)

    files = [
        _make_file("application/pdf", 800_000, "born_digital.pdf"),
        _make_file("application/pdf", 30_000_000, "heavy_scan.pdf", page_count=12),
        _make_file("image/png", 1_200_000, "scan.png"),
        _make_file(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            400_000,
            "note.docx",
        ),
    ]
    pkg = _make_package(files)

    decisions = [await router.decide(pkg, f) for f in files]

    chosen = {d.chosen_parser for d in decisions}
    assert AZURE_DOCUMENT_INTELLIGENCE_PARSER not in chosen
    assert chosen <= {"unstructured_fast", DOCLING_STANDARD_PARSER}

    for d in decisions:
        assert d.signals["cloud_ai_allowed"] is False
        assert d.reason != "scan_pdf_cloud_allowed_azure_di"


@pytest.mark.asyncio
async def test_profile_a_registry_never_resolves_azure_di(
    profile_a_engine: PolicyEngine,
    spy_registry: _SpyRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry lookup must never reach the Azure DI class under Profile A."""
    monkeypatch.setenv("AZURE_DOC_INTEL_ENDPOINT", "https://fake.azure.test/")
    monkeypatch.setenv("AZURE_DOC_INTEL_KEY", "dummy")

    router = MultiSignalRouter(policy_engine=profile_a_engine, registry=spy_registry)
    files = [
        _make_file("application/pdf", 800_000, "born_digital.pdf"),
        _make_file("image/png", 900_000, "scan.png"),
        _make_file("application/pdf", 20_000_000, "big_scan.pdf", page_count=8),
    ]
    pkg = _make_package(files)

    for f in files:
        decision = await router.decide(pkg, f)
        if decision.chosen_parser != "skipped_policy":
            spy_registry.get_parser(decision.chosen_parser)

    assert AZURE_DOCUMENT_INTELLIGENCE_PARSER not in spy_registry.resolution_log


@pytest.mark.asyncio
async def test_azure_di_class_registered_only_if_extra_installed(
    spy_registry: _SpyRegistry,
) -> None:
    """Sanity — registry visibility mirrors the optional extra's state."""
    try:
        import azure.ai.documentintelligence  # noqa: F401

        assert AZURE_DOCUMENT_INTELLIGENCE_PARSER in spy_registry.list_parsers()
    except ImportError:
        assert AZURE_DOCUMENT_INTELLIGENCE_PARSER not in spy_registry.list_parsers()


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shield tests from ambient AZURE env vars on developer machines."""
    for var in ("AZURE_DOC_INTEL_ENDPOINT", "AZURE_DOC_INTEL_KEY"):
        if var in os.environ:
            monkeypatch.delenv(var, raising=False)
