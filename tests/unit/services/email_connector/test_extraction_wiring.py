"""
@test_registry:
    suite: services-unit
    component: services.email_connector.orchestrator (S135 extraction wiring)
    covers:
        - src/aiflow/services/email_connector/orchestrator.py
        - src/aiflow/core/config.py (UC3ExtractionSettings)
    phase: 1
    priority: critical
    estimated_duration_ms: 600
    requires_services: []
    tags: [classifier, extraction, uc3, sprint-q, s135, orchestrator, flag-gate]

Sprint Q / S135 — invoice_processor wiring behind the
``AIFLOW_UC3_EXTRACTION__ENABLED`` flag. Covers:

1. Flag OFF → no invoice_processor import, no ``extracted_fields`` key,
   no ``extracted_fields_persisted`` log event, no call to
   ``parse_invoice`` (verified via monkeypatched sentinel).
2. Flag ON + non-EXTRACT intent → skipped (intent_class gate).
3. Flag ON + EXTRACT intent + zero eligible files → skipped.
4. Flag ON + EXTRACT + PDF → extractor runs, fields merged, log event.
5. Failure paths: timeout, per-file failure, total budget breach.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from aiflow.core.config import UC3AttachmentIntentSettings, UC3ExtractionSettings
from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.services.classifier.service import ClassificationResult
from aiflow.services.email_connector import orchestrator as orch
from aiflow.services.email_connector.orchestrator import (
    _intent_class_is_extract,
    scan_and_classify,
)

pytestmark = pytest.mark.asyncio

_PDF_MIME = "application/pdf"


class _FakeAdapter:
    def __init__(self, packages: list[IntakePackage]) -> None:
        self._packages = list(packages)

    async def fetch_next(self) -> IntakePackage | None:
        return self._packages.pop(0) if self._packages else None

    async def acknowledge(self, package_id: UUID) -> None:
        return None


class _FakeSink:
    async def handle(self, package: IntakePackage) -> None:
        return None


class _InvoiceClassifier:
    """Returns ``invoice_received`` (EXTRACT intent_class)."""

    async def classify(
        self,
        *,
        text: str,
        schema_labels: Any = None,
        context: dict[str, Any] | None = None,
        strategy: str | None = None,
    ) -> ClassificationResult:
        return ClassificationResult(
            label="invoice_received",
            display_name="Invoice Received",
            confidence=0.85,
            method="keywords",
        )


class _InquiryClassifier:
    """Returns ``inquiry`` (INFORMATION_REQUEST intent_class — NOT extract)."""

    async def classify(
        self,
        *,
        text: str,
        schema_labels: Any = None,
        context: dict[str, Any] | None = None,
        strategy: str | None = None,
    ) -> ClassificationResult:
        return ClassificationResult(
            label="inquiry",
            display_name="Inquiry",
            confidence=0.85,
            method="keywords",
        )


class _FakeRun:
    def __init__(self) -> None:
        self.id = uuid4()


class _FakeRepo:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    async def create_workflow_run(
        self,
        workflow_name: str,
        workflow_version: str,
        input_data: dict[str, Any],
        *,
        skill_name: str | None = None,
    ) -> _FakeRun:
        return _FakeRun()

    async def update_workflow_run_status(
        self, run_id: UUID, status: str, *, output_data: dict[str, Any] | None = None
    ) -> None:
        self.updates.append({"run_id": run_id, "output_data": output_data or {}})


def _make_pdf(tmp_path: Path, name: str = "invoice.pdf") -> IntakeFile:
    p = tmp_path / name
    p.write_bytes(b"%PDF-1.4 stub")
    return IntakeFile(
        file_path=str(p),
        file_name=p.name,
        mime_type=_PDF_MIME,
        size_bytes=p.stat().st_size,
        sha256="0" * 64,
    )


def _make_package(tmp_path: Path, *, files: list[IntakeFile] | None = None) -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id="s135-test",
        files=files if files is not None else [],
        descriptions=[
            IntakeDescription(
                text="please find attached the invoice",
                language="en",
                role=DescriptionRole.EMAIL_BODY,
            )
        ],
    )


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


class TestIntentClassGate:
    def test_invoice_label_is_extract(self) -> None:
        r = ClassificationResult(label="invoice_received", confidence=0.7, method="keywords")
        assert _intent_class_is_extract(r) is True

    def test_order_label_is_extract(self) -> None:
        r = ClassificationResult(label="order", confidence=0.7, method="keywords")
        assert _intent_class_is_extract(r) is True

    def test_inquiry_label_is_not_extract(self) -> None:
        r = ClassificationResult(label="inquiry", confidence=0.7, method="keywords")
        assert _intent_class_is_extract(r) is False

    def test_unknown_label_is_not_extract(self) -> None:
        r = ClassificationResult(label="whatever_new", confidence=0.0, method="")
        assert _intent_class_is_extract(r) is False


async def test_flag_off_is_true_no_op(tmp_path: Path, monkeypatch) -> None:
    """Flag OFF → no invoice_processor import, no extracted_fields key."""
    adapter = _FakeAdapter([_make_package(tmp_path, files=[_make_pdf(tmp_path)])])
    repo = _FakeRepo()

    def _fail(*args, **kwargs):  # pragma: no cover
        raise AssertionError("parse_invoice must not be imported when flag is OFF")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice",
        _fail,
        raising=False,
    )
    settings_off = UC3ExtractionSettings(enabled=False)

    with capture_logs() as events:
        await scan_and_classify(
            adapter,
            _FakeSink(),
            _InvoiceClassifier(),
            repo,
            tenant_id="s135-off",
            extraction_settings=settings_off,
        )

    assert "extracted_fields" not in repo.updates[0]["output_data"]
    assert not [
        e
        for e in events
        if e.get("event") == "email_connector.scan_and_classify.extracted_fields_persisted"
    ]


async def test_flag_off_when_settings_omitted(tmp_path: Path) -> None:
    adapter = _FakeAdapter([_make_package(tmp_path, files=[_make_pdf(tmp_path)])])
    repo = _FakeRepo()
    await scan_and_classify(
        adapter, _FakeSink(), _InvoiceClassifier(), repo, tenant_id="s135-no-settings"
    )
    assert "extracted_fields" not in repo.updates[0]["output_data"]


async def test_flag_on_non_extract_intent_skipped(tmp_path: Path, monkeypatch) -> None:
    adapter = _FakeAdapter([_make_package(tmp_path, files=[_make_pdf(tmp_path)])])
    repo = _FakeRepo()

    def _fail(*args, **kwargs):  # pragma: no cover
        raise AssertionError("parse_invoice must not run for non-EXTRACT intents")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice",
        _fail,
        raising=False,
    )
    settings_on = UC3ExtractionSettings(enabled=True)
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InquiryClassifier(),
        repo,
        tenant_id="s135-inquiry",
        extraction_settings=settings_on,
    )
    assert "extracted_fields" not in repo.updates[0]["output_data"]


async def test_flag_on_no_files_skipped(monkeypatch) -> None:
    adapter = _FakeAdapter([_make_package(Path("."), files=[])])
    repo = _FakeRepo()

    def _fail(*args, **kwargs):  # pragma: no cover
        raise AssertionError("parse_invoice must not run without files")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice",
        _fail,
        raising=False,
    )
    settings_on = UC3ExtractionSettings(enabled=True)
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InvoiceClassifier(),
        repo,
        tenant_id="s135-empty-files",
        extraction_settings=settings_on,
    )
    assert "extracted_fields" not in repo.updates[0]["output_data"]


async def test_flag_on_extract_path_merges_fields(tmp_path: Path, monkeypatch) -> None:
    """Happy path — stubbed extractor returns fields, they land in output_data."""
    pdf = _make_pdf(tmp_path, "supplier_invoice.pdf")
    adapter = _FakeAdapter([_make_package(tmp_path, files=[pdf])])
    repo = _FakeRepo()

    async def _fake_parse(data: dict) -> dict:
        return {
            "files": [
                {
                    "filename": Path(data["source_path"]).name,
                    "raw_text": "INV-2026-0042",
                    "raw_markdown": "",
                }
            ],
            "direction_hint": data.get("direction", "auto"),
            "source_path": data["source_path"],
        }

    async def _fake_extract(data: dict) -> dict:
        for f in data["files"]:
            f["vendor"] = {"name": "Acme Ltd"}
            f["buyer"] = {"name": "Customer Kft"}
            f["header"] = {"invoice_number": "INV-2026-0042", "currency": "EUR"}
            f["line_items"] = [{"description": "Consulting", "total": 100.0}]
            f["totals"] = {"gross_total": 127.0}
            f["extraction_confidence"] = 0.92
            f["extraction_time_ms"] = 1500.0
            f["_llm_total_input_tokens"] = 1400
            f["_llm_total_output_tokens"] = 250
        return data

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _fake_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data", _fake_extract
    )
    settings_on = UC3ExtractionSettings(enabled=True, total_budget_seconds=5.0)

    with capture_logs() as events:
        await scan_and_classify(
            adapter,
            _FakeSink(),
            _InvoiceClassifier(),
            repo,
            tenant_id="s135-happy",
            extraction_settings=settings_on,
        )

    output = repo.updates[0]["output_data"]
    assert "extracted_fields" in output
    fields = output["extracted_fields"]["supplier_invoice.pdf"]
    assert fields["header"]["invoice_number"] == "INV-2026-0042"
    assert fields["totals"]["gross_total"] == 127.0
    assert fields["cost_usd"] >= 0.0
    # log event fired
    assert [
        e
        for e in events
        if e.get("event") == "email_connector.scan_and_classify.extracted_fields_persisted"
    ]


async def test_flag_on_per_file_failure_isolated(tmp_path: Path, monkeypatch) -> None:
    """One bad attachment → captured as error entry, other files still extracted."""
    ok_pdf = _make_pdf(tmp_path, "ok.pdf")
    bad_pdf = _make_pdf(tmp_path, "bad.pdf")
    adapter = _FakeAdapter([_make_package(tmp_path, files=[ok_pdf, bad_pdf])])
    repo = _FakeRepo()

    async def _fake_parse(data: dict) -> dict:
        name = Path(data["source_path"]).name
        if name == "bad.pdf":
            raise RuntimeError("docling blew up")
        return {
            "files": [{"filename": name, "raw_text": "x"}],
            "direction_hint": "auto",
            "source_path": data["source_path"],
        }

    async def _fake_extract(data: dict) -> dict:
        for f in data["files"]:
            f["header"] = {"invoice_number": "X"}
            f["vendor"] = {}
            f["buyer"] = {}
            f["line_items"] = []
            f["totals"] = {}
            f["extraction_confidence"] = 0.5
            f["extraction_time_ms"] = 100.0
            f["_llm_total_input_tokens"] = 100
            f["_llm_total_output_tokens"] = 50
        return data

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _fake_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data", _fake_extract
    )
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InvoiceClassifier(),
        repo,
        tenant_id="s135-per-file",
        extraction_settings=UC3ExtractionSettings(enabled=True),
    )

    extracted = repo.updates[0]["output_data"]["extracted_fields"]
    assert "ok.pdf" in extracted and "header" in extracted["ok.pdf"]
    assert "bad.pdf" in extracted and "error" in extracted["bad.pdf"]


async def test_flag_on_timeout_returns_no_key(tmp_path: Path, monkeypatch) -> None:
    """Budget breach → helper returns None, orchestrator skips the key."""
    pdf = _make_pdf(tmp_path)
    adapter = _FakeAdapter([_make_package(tmp_path, files=[pdf])])
    repo = _FakeRepo()

    async def _slow_parse(data: dict) -> dict:
        await asyncio.sleep(2.0)
        return {"files": []}

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _slow_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data",
        lambda d: d,  # never reached
    )
    settings_on = UC3ExtractionSettings(enabled=True, total_budget_seconds=0.05)

    with capture_logs() as events:
        await scan_and_classify(
            adapter,
            _FakeSink(),
            _InvoiceClassifier(),
            repo,
            tenant_id="s135-timeout",
            extraction_settings=settings_on,
        )

    assert "extracted_fields" not in repo.updates[0]["output_data"]
    assert [
        e
        for e in events
        if e.get("event") == "email_connector.scan_and_classify.invoice_extract_timeout"
    ]


async def test_flag_on_non_pdf_attachment_ignored(tmp_path: Path, monkeypatch) -> None:
    """A non-PDF/DOCX attachment is filtered before extraction."""
    note = IntakeFile(
        file_path=str((tmp_path / "note.txt").resolve()),
        file_name="note.txt",
        mime_type="text/plain",
        size_bytes=1,
        sha256="0" * 64,
    )
    (tmp_path / "note.txt").write_text("hello")
    adapter = _FakeAdapter([_make_package(tmp_path, files=[note])])
    repo = _FakeRepo()

    async def _fake_parse(data: dict) -> dict:
        return {"files": []}

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _fake_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data", lambda d: d
    )
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InvoiceClassifier(),
        repo,
        tenant_id="s135-txt",
        extraction_settings=UC3ExtractionSettings(enabled=True),
    )
    extracted = repo.updates[0]["output_data"].get("extracted_fields")
    # The helper returned an empty dict for the filtered-out list.
    assert extracted == {}


async def test_flag_on_max_attachments_honored(tmp_path: Path, monkeypatch) -> None:
    """``max_attachments_per_email`` truncates the list before extraction."""
    pdfs = [_make_pdf(tmp_path, f"inv_{i}.pdf") for i in range(4)]
    adapter = _FakeAdapter([_make_package(tmp_path, files=pdfs)])
    repo = _FakeRepo()

    call_count = {"n": 0}

    async def _fake_parse(data: dict) -> dict:
        call_count["n"] += 1
        return {
            "files": [{"filename": Path(data["source_path"]).name, "raw_text": "x"}],
            "direction_hint": "auto",
        }

    async def _fake_extract(data: dict) -> dict:
        for f in data["files"]:
            f.update(
                {
                    "vendor": {},
                    "buyer": {},
                    "header": {},
                    "line_items": [],
                    "totals": {},
                    "extraction_confidence": 0.0,
                    "extraction_time_ms": 0.0,
                    "_llm_total_input_tokens": 1,
                    "_llm_total_output_tokens": 1,
                }
            )
        return data

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _fake_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data", _fake_extract
    )
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InvoiceClassifier(),
        repo,
        tenant_id="s135-max",
        extraction_settings=UC3ExtractionSettings(enabled=True, max_attachments_per_email=2),
    )
    extracted = repo.updates[0]["output_data"]["extracted_fields"]
    assert len(extracted) == 2
    assert call_count["n"] == 2


async def test_flag_on_classifier_method_unchanged(tmp_path: Path, monkeypatch) -> None:
    """The classifier's ``method`` string must not grow an ``+extraction`` suffix."""
    pdf = _make_pdf(tmp_path)
    adapter = _FakeAdapter([_make_package(tmp_path, files=[pdf])])
    repo = _FakeRepo()

    async def _fake_parse(data: dict) -> dict:
        return {
            "files": [{"filename": Path(data["source_path"]).name, "raw_text": "x"}],
            "direction_hint": "auto",
        }

    async def _fake_extract(data: dict) -> dict:
        for f in data["files"]:
            f.update(
                {
                    "vendor": {},
                    "buyer": {},
                    "header": {},
                    "line_items": [],
                    "totals": {},
                    "extraction_confidence": 0.0,
                    "extraction_time_ms": 0.0,
                    "_llm_total_input_tokens": 1,
                    "_llm_total_output_tokens": 1,
                }
            )
        return data

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _fake_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data", _fake_extract
    )
    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InvoiceClassifier(),
        repo,
        tenant_id="s135-method",
        extraction_settings=UC3ExtractionSettings(enabled=True),
    )
    # The classifier's method was "keywords" — extraction wiring should NOT
    # append anything; that's the attachment_rule's job (Sprint O).
    assert repo.updates[0]["output_data"]["method"] == "keywords"


async def test_cross_sprint_coexistence_with_attachment_intent(tmp_path: Path, monkeypatch) -> None:
    """Both Sprint O attachment-intent and Sprint Q extraction can fire on the
    same email. Output carries attachment_features AND extracted_fields."""
    pdf = _make_pdf(tmp_path)
    adapter = _FakeAdapter([_make_package(tmp_path, files=[pdf])])
    repo = _FakeRepo()

    # Stub the Sprint O attachment processor to return a clean signal.
    from aiflow.tools.attachment_processor import ProcessedAttachment

    class _StubProc:
        def __init__(self, *args, **kwargs): ...

        async def process(self, filename, content, mime_type):
            return ProcessedAttachment(
                filename=filename,
                mime_type=mime_type,
                text="INV-2026-0042 Total: 100 EUR",
                processor_used="stub",
            )

    monkeypatch.setattr("aiflow.tools.attachment_processor.AttachmentProcessor", _StubProc)

    async def _fake_parse(data: dict) -> dict:
        return {
            "files": [{"filename": Path(data["source_path"]).name, "raw_text": "x"}],
            "direction_hint": "auto",
        }

    async def _fake_extract(data: dict) -> dict:
        for f in data["files"]:
            f.update(
                {
                    "vendor": {"name": "A"},
                    "buyer": {"name": "B"},
                    "header": {"invoice_number": "INV-2026-0042"},
                    "line_items": [],
                    "totals": {"gross_total": 100},
                    "extraction_confidence": 0.9,
                    "extraction_time_ms": 10.0,
                    "_llm_total_input_tokens": 1,
                    "_llm_total_output_tokens": 1,
                }
            )
        return data

    monkeypatch.setattr("skills.invoice_processor.workflows.process.parse_invoice", _fake_parse)
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data", _fake_extract
    )

    await scan_and_classify(
        adapter,
        _FakeSink(),
        _InvoiceClassifier(),
        repo,
        tenant_id="s135-both",
        attachment_intent_settings=UC3AttachmentIntentSettings(
            enabled=True, total_budget_seconds=5.0, classifier_strategy="sklearn_only"
        ),
        extraction_settings=UC3ExtractionSettings(enabled=True, total_budget_seconds=5.0),
    )

    out = repo.updates[0]["output_data"]
    assert "attachment_features" in out
    assert "extracted_fields" in out
    assert out["extracted_fields"][pdf.file_name]["header"]["invoice_number"] == "INV-2026-0042"


# Keep orchestrator module usage visible to ruff after sub-edits.
_RUNTIME_HOOK = (orch,)
