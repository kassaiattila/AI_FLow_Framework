"""
@test_registry:
    suite: services-unit
    component: services.email_connector.orchestrator
    covers: [src/aiflow/services/email_connector/orchestrator.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [classifier, attachment, uc3, sprint-o, orchestrator, flag-gate]

UC3 Sprint O / S127 — flag-gate contract for the attachment-feature
extraction hook in ``scan_and_classify``. Validates:

1. Flag OFF → no ``attachment_features`` key in ``output_data``, no
   ``attachment_features_extracted`` log event, ``AttachmentProcessor`` is
   never instantiated (verified via monkeypatched constructor).
2. Flag ON + zero files → no extraction (guarded by the empty-files check).
3. Flag ON + a real on-disk attachment → ``attachment_features`` is merged
   into ``output_data`` and the structlog event fires.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from aiflow.core.config import UC3AttachmentIntentSettings
from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.services.classifier.service import ClassificationResult
from aiflow.services.email_connector import orchestrator as orch
from aiflow.services.email_connector.orchestrator import scan_and_classify

pytestmark = pytest.mark.asyncio


# -----------------------------------------------------------------------------
# Fakes — keep this test purely unit-level (no DB, no real classifier).
# -----------------------------------------------------------------------------


class _FakeAdapter:
    def __init__(self, packages: list[IntakePackage]) -> None:
        self._packages = list(packages)
        self.acked: list[UUID] = []

    async def fetch_next(self) -> IntakePackage | None:
        return self._packages.pop(0) if self._packages else None

    async def acknowledge(self, package_id: UUID) -> None:
        self.acked.append(package_id)


class _FakeSink:
    def __init__(self) -> None:
        self.handled: list[IntakePackage] = []

    async def handle(self, package: IntakePackage) -> None:
        self.handled.append(package)


class _FakeClassifier:
    async def classify(self, *, text: str, schema_labels: Any = None) -> ClassificationResult:
        return ClassificationResult(
            label="invoice_question",
            display_name="Invoice Question",
            confidence=0.42,
            method="sklearn_only",
            sub_label=None,
            reasoning="",
        )


class _FakeRun:
    def __init__(self) -> None:
        self.id = uuid4()


class _FakeRepo:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []

    async def create_workflow_run(
        self,
        workflow_name: str,
        workflow_version: str,
        input_data: dict[str, Any],
        *,
        skill_name: str | None = None,
    ) -> _FakeRun:
        self.created.append(
            {
                "workflow_name": workflow_name,
                "workflow_version": workflow_version,
                "input_data": input_data,
                "skill_name": skill_name,
            }
        )
        return _FakeRun()

    async def update_workflow_run_status(
        self,
        run_id: UUID,
        status: str,
        *,
        output_data: dict[str, Any] | None = None,
    ) -> None:
        self.updates.append({"run_id": run_id, "status": status, "output_data": output_data or {}})


def _make_package(
    *,
    tenant_id: str,
    body: str = "Please find attached the March invoice.",
    files: list[IntakeFile] | None = None,
) -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id=tenant_id,
        files=files or [],
        descriptions=[
            IntakeDescription(text=body, language="en", role=DescriptionRole.EMAIL_BODY),
        ],
    )


def _real_intake_file(tmp_path: Path) -> IntakeFile:
    """A small text file persisted to disk so AttachmentProcessor can read it."""
    p = tmp_path / "invoice_INV-2026-0042.txt"
    p.write_text(
        "Invoice INV-2026-0042\nTotal: 48,500 HUF\n",
        encoding="utf-8",
    )
    return IntakeFile(
        file_path=str(p),
        file_name=p.name,
        mime_type="text/plain",
        size_bytes=p.stat().st_size,
        sha256="0" * 64,
    )


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


async def test_flag_off_is_true_no_op(tmp_path: Path, monkeypatch) -> None:
    """Flag OFF: no AttachmentProcessor instantiation, no log event, no key."""
    adapter = _FakeAdapter([_make_package(tenant_id="t1", files=[_real_intake_file(tmp_path)])])
    sink = _FakeSink()
    repo = _FakeRepo()
    classifier = _FakeClassifier()

    instantiations: list[Any] = []

    def _spy_processor(*args, **kwargs):  # pragma: no cover — should never run
        instantiations.append((args, kwargs))
        raise AssertionError("AttachmentProcessor must not be instantiated when flag is OFF")

    monkeypatch.setattr("aiflow.tools.attachment_processor.AttachmentProcessor", _spy_processor)

    settings_off = UC3AttachmentIntentSettings(enabled=False)

    with capture_logs() as events:
        results = await scan_and_classify(
            adapter,
            sink,
            classifier,
            repo,
            tenant_id="t1",
            attachment_intent_settings=settings_off,
        )

    assert len(results) == 1
    assert instantiations == []
    assert "attachment_features" not in repo.updates[0]["output_data"]
    extract_events = [
        e
        for e in events
        if e.get("event") == "email_connector.scan_and_classify.attachment_features_extracted"
    ]
    assert extract_events == []


async def test_flag_off_default_when_settings_omitted(tmp_path: Path, monkeypatch) -> None:
    """Backward-compat: omitting the kwarg keeps Sprint K behaviour intact."""
    adapter = _FakeAdapter([_make_package(tenant_id="t1", files=[_real_intake_file(tmp_path)])])
    repo = _FakeRepo()

    def _spy_processor(*args, **kwargs):  # pragma: no cover
        raise AssertionError("AttachmentProcessor must not run without explicit flag-on settings")

    monkeypatch.setattr("aiflow.tools.attachment_processor.AttachmentProcessor", _spy_processor)

    await scan_and_classify(adapter, _FakeSink(), _FakeClassifier(), repo, tenant_id="t1")
    assert "attachment_features" not in repo.updates[0]["output_data"]


async def test_flag_on_zero_files_skips_extraction(monkeypatch) -> None:
    """Flag ON + empty files → guarded by ``package.files`` check, no extraction."""
    adapter = _FakeAdapter([_make_package(tenant_id="t2", files=[])])
    repo = _FakeRepo()

    instantiations: list[Any] = []

    def _spy_processor(*args, **kwargs):  # pragma: no cover
        instantiations.append((args, kwargs))
        raise AssertionError("AttachmentProcessor must not run when there are zero files")

    monkeypatch.setattr("aiflow.tools.attachment_processor.AttachmentProcessor", _spy_processor)

    settings_on = UC3AttachmentIntentSettings(enabled=True)
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _FakeClassifier(),
        repo,
        tenant_id="t2",
        attachment_intent_settings=settings_on,
    )

    assert instantiations == []
    assert "attachment_features" not in repo.updates[0]["output_data"]


async def test_flag_on_real_file_emits_features_and_event(tmp_path: Path) -> None:
    """End-to-end happy path: real on-disk text attachment flows through the
    extractor and lands in ``output_data['attachment_features']``."""
    adapter = _FakeAdapter([_make_package(tenant_id="t3", files=[_real_intake_file(tmp_path)])])
    repo = _FakeRepo()

    settings_on = UC3AttachmentIntentSettings(enabled=True, total_budget_seconds=30.0)

    with capture_logs() as events:
        await scan_and_classify(
            adapter,
            _FakeSink(),
            _FakeClassifier(),
            repo,
            tenant_id="t3",
            attachment_intent_settings=settings_on,
        )

    assert len(repo.updates) == 1
    payload = repo.updates[0]["output_data"]
    assert "attachment_features" in payload
    features = payload["attachment_features"]
    assert features["invoice_number_detected"] is True
    assert features["total_value_detected"] is True
    assert features["mime_profile"] == "text/plain"
    assert features["attachments_considered"] == 1

    extract_events = [
        e
        for e in events
        if e.get("event") == "email_connector.scan_and_classify.attachment_features_extracted"
    ]
    assert len(extract_events) == 1
    assert extract_events[0]["invoice_number_detected"] is True


async def test_helper_returns_none_on_timeout(monkeypatch, tmp_path: Path) -> None:
    """Asyncio.wait_for breach returns ``None`` and emits a timeout log event."""
    file_a = _real_intake_file(tmp_path)
    settings_on = UC3AttachmentIntentSettings(enabled=True, total_budget_seconds=0.01)

    class _SlowProcessor:
        def __init__(self, *args, **kwargs):
            pass

        async def process(self, *args, **kwargs):
            import asyncio

            await asyncio.sleep(2.0)
            raise AssertionError("should have timed out")

    monkeypatch.setattr("aiflow.tools.attachment_processor.AttachmentProcessor", _SlowProcessor)

    with capture_logs() as events:
        out = await orch._maybe_extract_attachment_features([file_a], settings=settings_on)

    assert out is None
    timeout_events = [
        e
        for e in events
        if e.get("event") == "email_connector.scan_and_classify.attachment_extraction_timeout"
    ]
    assert len(timeout_events) == 1
