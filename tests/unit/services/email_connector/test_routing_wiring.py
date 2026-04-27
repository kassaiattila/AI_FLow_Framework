"""
@test_registry:
    suite: services-unit
    component: services.email_connector.orchestrator (SX-2 routing layer)
    covers:
        - src/aiflow/services/email_connector/orchestrator.py (_route_extract_by_doctype)
        - src/aiflow/contracts/uc3_routing.py
        - src/aiflow/core/config.py (UC3DocRecognizerRoutingSettings)
    phase: 1
    priority: critical
    estimated_duration_ms: 800
    requires_services: []
    tags: [classifier, extraction, uc3, sprint-x, sx2, routing, doc-recognizer, flag-gate]

Sprint X / SX-2 — UC3 EXTRACT routing through DocRecognizer.

Covers the 10 unit acceptance gates from session_prompts/NEXT.md:

1. Settings defaults (flag off, threshold 0.6, budget 30s, fallback).
2. ``hu_invoice`` doctype dispatches to invoice_processor (UC1 byte-stable).
3. Other known doctypes (id_card, address_card, passport, contract) dispatch
   to DocRecognizer's run().
4. Below-threshold falls through per ``unknown_doctype_action``.
5. ``unknown_doctype_action="fallback_invoice_processor"`` calls invoice path.
6. ``unknown_doctype_action="rag_ingest"`` records the rag_ingest stub.
7. ``unknown_doctype_action="skip"`` skips with no extractor call.
8. Per-attachment error isolation — one bad attachment doesn't poison rest.
9. Cost preflight ceiling refusal sets ``extraction_outcome="refused_cost"``.
10. Per-attachment timeout returns partial results (timed_out marker).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,
    DocIntentDecision,
    DocTypeMatch,
)
from aiflow.core.config import UC3DocRecognizerRoutingSettings, UC3ExtractionSettings
from aiflow.guardrails.cost_preflight import PreflightDecision
from aiflow.intake.package import IntakeFile
from aiflow.services.email_connector.orchestrator import _route_extract_by_doctype

pytestmark = pytest.mark.asyncio


_PDF_MIME = "application/pdf"


def _make_pdf(tmp_path: Path, name: str = "doc.pdf") -> IntakeFile:
    p = tmp_path / name
    p.write_bytes(b"%PDF-1.4 stub")
    return IntakeFile(
        file_path=str(p),
        file_name=name,
        mime_type=_PDF_MIME,
        size_bytes=p.stat().st_size,
        sha256="0" * 64,
    )


class _FakeDocRecognizer:
    """Stub DocumentRecognizerOrchestrator with deterministic classify/run."""

    def __init__(
        self,
        *,
        match: DocTypeMatch | None,
        extraction: DocExtractionResult | None = None,
        intent: DocIntentDecision | None = None,
        classify_delay: float = 0.0,
        run_delay: float = 0.0,
        run_raises: BaseException | None = None,
    ) -> None:
        self._match = match
        self._extraction = extraction
        self._intent = intent or DocIntentDecision(intent="process", reason="stub")
        self._classify_delay = classify_delay
        self._run_delay = run_delay
        self._run_raises = run_raises
        self.classify_calls: list[str] = []
        self.run_calls: list[tuple[str, str | None]] = []

    async def classify(self, ctx: Any, *, tenant_id: str, doc_type_hint: str | None = None):
        self.classify_calls.append(tenant_id)
        if self._classify_delay:
            await asyncio.sleep(self._classify_delay)
        if self._match is None:
            return None, None
        return self._match, MagicMock(name="descriptor")

    async def run(self, ctx: Any, *, tenant_id: str, doc_type_hint: str | None = None):
        self.run_calls.append((tenant_id, doc_type_hint))
        if self._run_raises is not None:
            raise self._run_raises
        if self._run_delay:
            await asyncio.sleep(self._run_delay)
        if self._extraction is None:
            return None
        return self._match, self._extraction, self._intent


class _FakePreflight:
    def __init__(self, *, allow: bool) -> None:
        self._allow = allow
        self.calls: list[str] = []

    def check_step(
        self,
        *,
        step_name: str,
        model: str,
        input_tokens: int,
        max_output_tokens: int,
        ceiling_usd: float | None,
    ) -> PreflightDecision:
        self.calls.append(step_name)
        return PreflightDecision(
            allowed=self._allow,
            projected_usd=0.001,
            remaining_usd=None,
            reason=("step_under_ceiling" if self._allow else "step_over_ceiling"),
            period="daily",
            dry_run=False,
        )


def _stub_invoice_processor(
    monkeypatch: pytest.MonkeyPatch, *, raise_on: str | None = None
) -> dict:
    """Patch parse_invoice / extract_invoice_data to deterministic stubs.

    Returns a counter dict so tests can assert how many times the extractor
    fired (per call equals one attachment routed to invoice_processor).
    """
    counter = {"parse": 0, "extract": 0}

    async def _parse(data: dict) -> dict:
        counter["parse"] += 1
        name = Path(data["source_path"]).name
        if raise_on and name == raise_on:
            raise RuntimeError("docling stub failure")
        return {
            "files": [{"filename": name, "raw_text": "stub"}],
            "direction_hint": "auto",
            "source_path": data["source_path"],
        }

    async def _extract(data: dict) -> dict:
        counter["extract"] += 1
        for f in data["files"]:
            f.update(
                {
                    "vendor": {"name": "Acme"},
                    "buyer": {"name": "Customer"},
                    "header": {"invoice_number": "INV-2026-0001"},
                    "line_items": [],
                    "totals": {"gross_total": 100},
                    "extraction_confidence": 0.92,
                    "extraction_time_ms": 50.0,
                    "_llm_total_input_tokens": 1500,
                    "_llm_total_output_tokens": 300,
                }
            )
        return data

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice", _parse, raising=False
    )
    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.extract_invoice_data",
        _extract,
        raising=False,
    )
    return counter


def _stub_attachment_processor(monkeypatch: pytest.MonkeyPatch, *, text: str = "stub text") -> None:
    """Replace AttachmentProcessor with a stub that returns deterministic text."""
    from aiflow.tools.attachment_processor import ProcessedAttachment

    class _StubProc:
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

        async def process(
            self, filename: str, content: bytes, mime_type: str
        ) -> ProcessedAttachment:
            return ProcessedAttachment(
                filename=filename,
                mime_type=mime_type,
                text=text,
                processor_used="stub",
            )

    monkeypatch.setattr("aiflow.tools.attachment_processor.AttachmentProcessor", _StubProc)


# ---------------------------------------------------------------------------
# 1. Settings defaults
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    async def test_settings_defaults(self) -> None:
        s = UC3DocRecognizerRoutingSettings()
        assert s.enabled is False
        assert s.confidence_threshold == pytest.approx(0.6)
        assert s.total_budget_seconds == pytest.approx(30.0)
        assert s.unknown_doctype_action == "fallback_invoice_processor"


# ---------------------------------------------------------------------------
# 2. hu_invoice → invoice_processor
# ---------------------------------------------------------------------------


async def test_route_dispatches_hu_invoice_to_invoice_processor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = _stub_invoice_processor(monkeypatch)
    _stub_attachment_processor(monkeypatch)
    pdf = _make_pdf(tmp_path, "supplier_invoice.pdf")
    fake = _FakeDocRecognizer(match=DocTypeMatch(doc_type="hu_invoice", confidence=0.9))

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True),
        extraction_settings=UC3ExtractionSettings(enabled=True, total_budget_seconds=5.0),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    assert payload is not None
    assert counter["parse"] == 1 and counter["extract"] == 1
    assert "supplier_invoice.pdf" in payload["extracted_fields"]
    rd = payload["routing_decision"]
    assert rd["attachments"][0]["doctype_detected"] == "hu_invoice"
    assert rd["attachments"][0]["extraction_path"] == "invoice_processor"
    assert rd["attachments"][0]["extraction_outcome"] == "succeeded"
    assert fake.run_calls == []  # invoice_processor does not call DocRecognizer.run()


# ---------------------------------------------------------------------------
# 3. Other doctypes → DocRecognizer.run()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "doctype",
    ["hu_id_card", "hu_address_card", "eu_passport", "pdf_contract"],
)
async def test_route_dispatches_other_doctypes_to_doc_recognizer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    doctype: str,
) -> None:
    _stub_attachment_processor(monkeypatch)

    def _no_invoice(*args: Any, **kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("invoice_processor must not run for non-invoice doctypes")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice", _no_invoice, raising=False
    )

    pdf = _make_pdf(tmp_path, f"{doctype}.pdf")
    extraction = DocExtractionResult(
        doc_type=doctype,
        extracted_fields={
            "field_a": DocFieldValue(value="X", confidence=0.85),
            "field_b": DocFieldValue(value="Y", confidence=0.75),
            "field_c": DocFieldValue(value="Z", confidence=0.7),
        },
        cost_usd=0.002,
        extraction_time_ms=100.0,
    )
    fake = _FakeDocRecognizer(
        match=DocTypeMatch(doc_type=doctype, confidence=0.95),
        extraction=extraction,
        intent=DocIntentDecision(intent="process", reason="rule"),
    )

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True),
        extraction_settings=UC3ExtractionSettings(enabled=True),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    assert payload is not None
    rd = payload["routing_decision"]
    assert rd["attachments"][0]["extraction_path"] == "doc_recognizer_workflow"
    assert rd["attachments"][0]["doctype_detected"] == doctype
    assert rd["attachments"][0]["extraction_outcome"] == "succeeded"
    fields = payload["extracted_fields"][f"{doctype}.pdf"]
    assert fields["doc_type"] == doctype
    assert set(fields["extracted_fields"].keys()) == {"field_a", "field_b", "field_c"}
    assert fake.run_calls == [("tenant-x", doctype)]


# ---------------------------------------------------------------------------
# 4. Below threshold → falls through per policy (default fallback)
# ---------------------------------------------------------------------------


async def test_below_threshold_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = _stub_invoice_processor(monkeypatch)
    _stub_attachment_processor(monkeypatch)
    pdf = _make_pdf(tmp_path, "ambiguous.pdf")
    fake = _FakeDocRecognizer(match=DocTypeMatch(doc_type="hu_id_card", confidence=0.4))

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True, confidence_threshold=0.6),
        extraction_settings=UC3ExtractionSettings(enabled=True, total_budget_seconds=5.0),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    assert payload is not None
    # Default action is fallback_invoice_processor — it ran.
    assert counter["parse"] == 1
    rd = payload["routing_decision"]
    assert rd["attachments"][0]["extraction_path"] == "invoice_processor"
    assert rd["attachments"][0]["doctype_confidence"] == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# 5. unknown_doctype_action="fallback_invoice_processor" (explicit)
# ---------------------------------------------------------------------------


async def test_unknown_doctype_action_fallback_invoice_processor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = _stub_invoice_processor(monkeypatch)
    _stub_attachment_processor(monkeypatch)
    pdf = _make_pdf(tmp_path, "unknown.pdf")
    # No match at all — registry empty / classifier returned None.
    fake = _FakeDocRecognizer(match=None)

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(
            enabled=True, unknown_doctype_action="fallback_invoice_processor"
        ),
        extraction_settings=UC3ExtractionSettings(enabled=True, total_budget_seconds=5.0),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    assert counter["parse"] == 1
    rd = payload["routing_decision"]  # type: ignore[index]
    assert rd["attachments"][0]["extraction_path"] == "invoice_processor"
    assert rd["attachments"][0]["doctype_detected"] is None


# ---------------------------------------------------------------------------
# 6. unknown_doctype_action="rag_ingest"
# ---------------------------------------------------------------------------


async def test_unknown_doctype_action_rag_ingest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_attachment_processor(monkeypatch)

    def _no_invoice(*a: Any, **kw: Any) -> None:  # pragma: no cover
        raise AssertionError("invoice_processor must not run for rag_ingest policy")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice", _no_invoice, raising=False
    )

    pdf = _make_pdf(tmp_path, "weird.pdf")
    fake = _FakeDocRecognizer(match=None)

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(
            enabled=True, unknown_doctype_action="rag_ingest"
        ),
        extraction_settings=UC3ExtractionSettings(enabled=True),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    rd = payload["routing_decision"]  # type: ignore[index]
    assert rd["attachments"][0]["extraction_path"] == "rag_ingest"
    assert payload["extracted_fields"]["weird.pdf"] == {"rag_ingest": "queued"}  # type: ignore[index]


# ---------------------------------------------------------------------------
# 7. unknown_doctype_action="skip"
# ---------------------------------------------------------------------------


async def test_unknown_doctype_action_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_attachment_processor(monkeypatch)

    def _no_invoice(*a: Any, **kw: Any) -> None:  # pragma: no cover
        raise AssertionError("invoice_processor must not run when skip policy is set")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice", _no_invoice, raising=False
    )

    pdf = _make_pdf(tmp_path, "doc.pdf")
    fake = _FakeDocRecognizer(match=DocTypeMatch(doc_type="hu_id_card", confidence=0.3))

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(
            enabled=True, unknown_doctype_action="skip"
        ),
        extraction_settings=UC3ExtractionSettings(enabled=True),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    rd = payload["routing_decision"]  # type: ignore[index]
    assert rd["attachments"][0]["extraction_path"] == "skipped"
    assert rd["attachments"][0]["extraction_outcome"] == "skipped"
    assert payload["extracted_fields"] == {}  # type: ignore[index]


# ---------------------------------------------------------------------------
# 8. Per-attachment error isolation
# ---------------------------------------------------------------------------


async def test_per_attachment_error_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_attachment_processor(monkeypatch)
    bad = _make_pdf(tmp_path, "bad.pdf")
    good = _make_pdf(tmp_path, "good.pdf")

    extraction = DocExtractionResult(
        doc_type="hu_id_card",
        extracted_fields={"name": DocFieldValue(value="Anna", confidence=0.9)},
        cost_usd=0.001,
        extraction_time_ms=10.0,
    )

    class _Selective(_FakeDocRecognizer):
        async def run(self, ctx: Any, *, tenant_id: str, doc_type_hint: str | None = None):
            self.run_calls.append((tenant_id, doc_type_hint))
            if ctx.filename == "bad.pdf":
                raise RuntimeError("simulated extractor crash")
            return self._match, self._extraction, self._intent

    fake = _Selective(
        match=DocTypeMatch(doc_type="hu_id_card", confidence=0.95),
        extraction=extraction,
        intent=DocIntentDecision(intent="process", reason="rule"),
    )

    payload = await _route_extract_by_doctype(
        [bad, good],
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True),
        extraction_settings=UC3ExtractionSettings(enabled=True),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    rd = payload["routing_decision"]  # type: ignore[index]
    by_filename = {row["filename"]: row for row in rd["attachments"]}
    assert by_filename["bad.pdf"]["extraction_outcome"] == "failed"
    assert by_filename["good.pdf"]["extraction_outcome"] == "succeeded"
    # Good attachment fields landed; bad attachment fields absent.
    assert "good.pdf" in payload["extracted_fields"]  # type: ignore[index]
    assert "bad.pdf" not in payload["extracted_fields"]  # type: ignore[index]


# ---------------------------------------------------------------------------
# 9. Cost preflight refusal
# ---------------------------------------------------------------------------


async def test_cost_ceiling_refusal_marks_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_attachment_processor(monkeypatch)

    def _no_invoice(*a: Any, **kw: Any) -> None:  # pragma: no cover
        raise AssertionError("invoice_processor must not run when preflight refuses")

    monkeypatch.setattr(
        "skills.invoice_processor.workflows.process.parse_invoice", _no_invoice, raising=False
    )

    pdf = _make_pdf(tmp_path, "expensive.pdf")
    fake = _FakeDocRecognizer(match=DocTypeMatch(doc_type="hu_invoice", confidence=0.95))
    preflight = _FakePreflight(allow=False)

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True),
        extraction_settings=UC3ExtractionSettings(enabled=True),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
        cost_preflight=preflight,
    )

    rd = payload["routing_decision"]  # type: ignore[index]
    assert rd["attachments"][0]["extraction_outcome"] == "refused_cost"
    assert rd["attachments"][0]["extraction_path"] == "invoice_processor"
    assert preflight.calls == ["uc3_routing.invoice_processor"]
    assert payload["extracted_fields"] == {}  # type: ignore[index]


# ---------------------------------------------------------------------------
# 10. Per-attachment timeout
# ---------------------------------------------------------------------------


async def test_total_budget_timeout_returns_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_attachment_processor(monkeypatch)
    pdf = _make_pdf(tmp_path, "slow.pdf")
    fake = _FakeDocRecognizer(
        match=DocTypeMatch(doc_type="hu_id_card", confidence=0.95),
        extraction=DocExtractionResult(
            doc_type="hu_id_card",
            extracted_fields={"x": DocFieldValue(value="x", confidence=0.9)},
        ),
        run_delay=2.0,
    )

    payload = await _route_extract_by_doctype(
        [pdf],
        routing_settings=UC3DocRecognizerRoutingSettings(enabled=True, total_budget_seconds=0.05),
        extraction_settings=UC3ExtractionSettings(enabled=True),
        tenant_id="tenant-x",
        doc_recognizer_orchestrator=fake,
    )

    rd = payload["routing_decision"]  # type: ignore[index]
    assert rd["attachments"][0]["extraction_outcome"] == "timed_out"
    assert payload["extracted_fields"] == {}  # type: ignore[index]
