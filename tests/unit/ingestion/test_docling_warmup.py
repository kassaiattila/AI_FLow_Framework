"""
@test_registry:
    suite: ingestion-unit
    component: ingestion.parsers.docling_parser (FU-4 warmup)
    covers:
        - src/aiflow/ingestion/parsers/docling_parser.py
        - scripts/warmup_docling.py
    phase: sprint-o-fu-4
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [ingestion, docling, warmup, sprint-o, fu-4]

Sprint O FU-4 — cold-start instrumentation. These tests cover the
graceful-degradation contract of ``DoclingParser.warmup``:

- Missing reportlab → returns warmed=False with a reason string (no raise).
- Missing docling → returns warmed=False with a reason string (no raise).
- Runtime failure during parse → warmed=False, reason carries the class name.
- Happy path is delegated to the integration test (real docling + reportlab
  runs the whole pipeline), since stubbing the converter defeats the point.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import patch

import pytest

from aiflow.ingestion.parsers.docling_parser import DoclingParser, WarmupResult


@pytest.fixture()
def _fake_reportlab() -> None:
    """Inject minimal reportlab stubs so warmup gets past the import guard.

    CI runners don't install reportlab (it's a dev-only dep for the Sprint O
    fixture generator + this warmup path). The warmup logic's import check
    returns early on ImportError; for tests targeting the parse-path error
    handling, we need to make the import succeed.
    """

    class _Canvas:
        # Method names mirror the real reportlab Canvas API (camelCase on
        # purpose). N802 disabled for the stub only.
        def __init__(self, *args, **kwargs): ...
        def setFont(self, *args, **kwargs): ...  # noqa: N802
        def drawString(self, *args, **kwargs): ...  # noqa: N802
        def showPage(self, *args, **kwargs): ...  # noqa: N802
        def save(self, *args, **kwargs): ...

    fake_canvas_mod = types.ModuleType("reportlab.pdfgen.canvas")
    fake_canvas_mod.Canvas = _Canvas
    fake_pdfgen_mod = types.ModuleType("reportlab.pdfgen")
    fake_pdfgen_mod.canvas = fake_canvas_mod
    fake_pagesizes_mod = types.ModuleType("reportlab.lib.pagesizes")
    fake_pagesizes_mod.A4 = (595, 842)
    fake_lib_mod = types.ModuleType("reportlab.lib")
    fake_lib_mod.pagesizes = fake_pagesizes_mod
    fake_reportlab_mod = types.ModuleType("reportlab")
    fake_reportlab_mod.lib = fake_lib_mod
    fake_reportlab_mod.pdfgen = fake_pdfgen_mod

    patched = {
        "reportlab": fake_reportlab_mod,
        "reportlab.lib": fake_lib_mod,
        "reportlab.lib.pagesizes": fake_pagesizes_mod,
        "reportlab.pdfgen": fake_pdfgen_mod,
        "reportlab.pdfgen.canvas": fake_canvas_mod,
    }
    with patch.dict(sys.modules, patched):
        yield


class TestWarmupModel:
    def test_warmup_result_defaults(self) -> None:
        r = WarmupResult()
        assert r.warmed is False
        assert r.elapsed_seconds == 0.0
        assert r.reason == ""
        assert r.file_type == ""


class TestWarmupGracefulDegradation:
    """Missing optional deps or runtime errors must not raise."""

    def test_missing_reportlab_reports_reason(self) -> None:
        with patch.dict(sys.modules, {"reportlab": None, "reportlab.pdfgen": None}):
            parser = DoclingParser()
            result = parser.warmup()
        assert result.warmed is False
        assert "reportlab" in result.reason.lower()
        assert result.elapsed_seconds == 0.0

    def test_parse_error_reports_classname(self, _fake_reportlab: None) -> None:
        """A runtime error from inside `parse` is captured, not raised."""
        parser = DoclingParser()
        with patch.object(parser, "parse", side_effect=RuntimeError("boom")):
            result = parser.warmup()
        assert result.warmed is False
        assert "RuntimeError" in result.reason
        assert "boom" in result.reason
        assert result.elapsed_seconds > 0.0

    def test_missing_docling_is_caught(self, _fake_reportlab: None) -> None:
        """ImportError raised by docling must fall through without crashing."""
        parser = DoclingParser()
        with patch.object(parser, "parse", side_effect=ImportError("docling missing")):
            result = parser.warmup()
        assert result.warmed is False
        assert "docling" in result.reason.lower()


class TestCliScriptContract:
    """The CLI wrapper translates WarmupResult into exit codes."""

    def test_cli_exit_code_zero_on_skip_without_strict(self) -> None:
        from scripts import warmup_docling

        dp = DoclingParser()
        with (
            patch.object(dp, "warmup", return_value=WarmupResult(warmed=False, reason="no deps")),
            patch.object(warmup_docling, "DoclingParser", return_value=dp),
        ):
            rc = warmup_docling.main([])
        assert rc == 0

    def test_cli_exit_code_two_on_skip_with_strict(self) -> None:
        from scripts import warmup_docling

        dp = DoclingParser()
        with (
            patch.object(dp, "warmup", return_value=WarmupResult(warmed=False, reason="no deps")),
            patch.object(warmup_docling, "DoclingParser", return_value=dp),
        ):
            rc = warmup_docling.main(["--strict"])
        assert rc == 2

    def test_cli_exit_code_zero_on_success(self) -> None:
        from scripts import warmup_docling

        dp = DoclingParser()
        with (
            patch.object(
                dp, "warmup", return_value=WarmupResult(warmed=True, elapsed_seconds=0.01)
            ),
            patch.object(warmup_docling, "DoclingParser", return_value=dp),
        ):
            rc = warmup_docling.main(["--strict"])
        assert rc == 0
