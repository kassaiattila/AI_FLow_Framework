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
from unittest.mock import patch

from aiflow.ingestion.parsers.docling_parser import DoclingParser, WarmupResult


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

    def test_parse_error_reports_classname(self) -> None:
        """A runtime error from inside `parse` is captured, not raised."""
        parser = DoclingParser()
        with patch.object(parser, "parse", side_effect=RuntimeError("boom")):
            result = parser.warmup()
        assert result.warmed is False
        assert "RuntimeError" in result.reason
        assert "boom" in result.reason
        assert result.elapsed_seconds > 0.0

    def test_missing_docling_is_caught(self) -> None:
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
