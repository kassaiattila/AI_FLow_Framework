"""
@test_registry:
    suite: unit-skills
    component: skills.invoice_processor (Sprint U S156)
    covers:
        - skills/invoice_processor/models/__init__.py (issue_date alias)
        - skills/invoice_processor/workflows/process.py (_parse_date_iso, dict normalize)
    phase: v1.5.4
    priority: high
    estimated_duration_ms: 80
    requires_services: []
    tags: [unit, skills, invoice_processor, sprint_u, s156, sq_fu_1, sq_fu_4]
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from skills.invoice_processor.models import InvoiceHeader
from skills.invoice_processor.workflows.process import _parse_date_iso


class TestInvoiceHeaderIssueDateAlias:
    """Sprint U S156 (SQ-FU-1) — issue_date is the canonical name; invoice_date alias preserved."""

    def test_construct_with_issue_date_keyword(self):
        h = InvoiceHeader(issue_date="2026-04-01")
        assert h.issue_date == "2026-04-01"
        assert h.invoice_date == "2026-04-01"  # backward-compat property

    def test_construct_with_invoice_date_alias(self):
        """Pydantic AliasChoices: a JSON dict with `invoice_date` still parses
        (pre-S156 JSONB rows + DB column reads)."""
        h = InvoiceHeader.model_validate({"invoice_date": "2026-04-15"})
        assert h.issue_date == "2026-04-15"
        assert h.invoice_date == "2026-04-15"

    def test_issue_date_takes_precedence_over_invoice_date(self):
        h = InvoiceHeader.model_validate({"issue_date": "2026-04-01", "invoice_date": "1999-01-01"})
        assert h.issue_date == "2026-04-01"
        assert h.invoice_date == "2026-04-01"

    def test_default_empty_string(self):
        h = InvoiceHeader()
        assert h.issue_date == ""
        assert h.invoice_date == ""


class TestParseDateIso:
    """Sprint U S156 (SQ-FU-4) — `_parse_date_iso` shape stability."""

    def test_iso_string_passes_through(self):
        assert _parse_date_iso("2026-04-15") == "2026-04-15"

    def test_iso_with_time_truncates_to_date(self):
        assert _parse_date_iso("2026-04-15T13:42:00") == "2026-04-15"

    def test_european_dot_format(self):
        assert _parse_date_iso("15.04.2026") == "2026-04-15"

    def test_european_slash_format(self):
        assert _parse_date_iso("15/04/2026") == "2026-04-15"

    def test_year_first_slash_format(self):
        assert _parse_date_iso("2026/04/15") == "2026-04-15"

    def test_date_object_isoformat(self):
        assert _parse_date_iso(date(2026, 4, 15)) == "2026-04-15"

    def test_datetime_object_truncates_to_date(self):
        assert _parse_date_iso(datetime(2026, 4, 15, 13, 42, 0)) == "2026-04-15"

    def test_none_returns_none(self):
        assert _parse_date_iso(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date_iso("") is None
        assert _parse_date_iso("   ") is None

    def test_unparseable_string_returns_none(self):
        assert _parse_date_iso("not a date") is None
        assert _parse_date_iso("yesterday") is None

    def test_invalid_calendar_date_returns_none(self):
        # February 30 doesn't exist
        assert _parse_date_iso("30.02.2026") is None
        assert _parse_date_iso("2026-02-30") is None

    def test_non_string_non_date_returns_none(self):
        assert _parse_date_iso(12345) is None
        assert _parse_date_iso({"date": "2026-04-15"}) is None


class TestArgparseOutputHelper:
    """Sprint U S156 (ST-FU-4) — uniform --output flag helper."""

    def test_argparse_output_adds_flags(self):
        import argparse

        from scripts._common import argparse_output

        parser = argparse.ArgumentParser()
        argparse_output(parser)
        args = parser.parse_args([])
        assert args.output == "text"  # default
        assert args.output_path == "-"

    def test_argparse_output_accepts_json(self):
        import argparse

        from scripts._common import argparse_output

        parser = argparse.ArgumentParser()
        argparse_output(parser)
        args = parser.parse_args(["--output", "json", "--output-path", "/tmp/x.json"])
        assert args.output == "json"
        assert args.output_path == "/tmp/x.json"

    def test_argparse_output_rejects_unknown_mode(self):
        import argparse

        from scripts._common import argparse_output

        parser = argparse.ArgumentParser()
        argparse_output(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(["--output", "xml"])

    def test_argparse_output_custom_default_mode(self):
        import argparse

        from scripts._common import argparse_output

        parser = argparse.ArgumentParser()
        argparse_output(parser, default_mode="jsonl")
        args = parser.parse_args([])
        assert args.output == "jsonl"

    def test_write_output_text_dict(self, tmp_path):
        from scripts._common import write_output

        target = tmp_path / "out.txt"
        write_output("text", str(target), {"a": 1, "b": "hello"})
        content = target.read_text(encoding="utf-8")
        assert "a: 1" in content
        assert "b: hello" in content

    def test_write_output_json_dict(self, tmp_path):
        import json

        from scripts._common import write_output

        target = tmp_path / "out.json"
        write_output("json", str(target), {"a": 1, "b": "hello"})
        parsed = json.loads(target.read_text(encoding="utf-8"))
        assert parsed == {"a": 1, "b": "hello"}

    def test_write_output_jsonl_list(self, tmp_path):
        import json

        from scripts._common import write_output

        target = tmp_path / "out.jsonl"
        write_output("jsonl", str(target), [{"a": 1}, {"b": 2}])
        lines = target.read_text(encoding="utf-8").strip().split("\n")
        assert json.loads(lines[0]) == {"a": 1}
        assert json.loads(lines[1]) == {"b": 2}

    def test_write_output_creates_parent_dirs(self, tmp_path):
        from scripts._common import write_output

        target = tmp_path / "deep" / "nested" / "out.json"
        write_output("json", str(target), {"x": 1})
        assert target.exists()

    def test_write_output_unknown_mode_raises(self, tmp_path):
        from scripts._common import write_output

        with pytest.raises(ValueError, match="unknown output mode"):
            write_output("xml", str(tmp_path / "x"), {})  # type: ignore[arg-type]
