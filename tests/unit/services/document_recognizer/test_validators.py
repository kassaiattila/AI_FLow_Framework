"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.validators
    covers:
        - src/aiflow/services/document_recognizer/validators.py
    phase: v1.7.0
    priority: critical
    estimated_duration_ms: 50
    requires_services: []
    tags: [unit, services, doc_recognizer, validators, sprint_w, sw_1]
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiflow.services.document_recognizer.validators import (
    after_today,
    apply_validators,
    before_today,
    iso_date,
    max_value,
    min_value,
    non_empty,
    regex_validator,
)


class TestNonEmpty:
    def test_non_empty_string(self):
        ok, w = non_empty("hello")
        assert ok is True and w is None

    def test_empty_string_fails(self):
        ok, w = non_empty("")
        assert ok is False and "empty string" in (w or "")

    def test_whitespace_only_fails(self):
        ok, w = non_empty("   ")
        assert ok is False

    def test_none_fails(self):
        ok, _ = non_empty(None)
        assert ok is False

    def test_empty_list_fails(self):
        ok, _ = non_empty([])
        assert ok is False

    def test_zero_passes(self):
        # Numeric 0 is non-empty; use min:1 for "must be positive"
        ok, _ = non_empty(0)
        assert ok is True

    def test_false_fails(self):
        ok, _ = non_empty(False)
        assert ok is False


class TestRegex:
    def test_full_match_passes(self):
        ok, _ = regex_validator("INV-2026-0001", r"^INV-\d{4}-\d{4}$")
        assert ok is True

    def test_partial_match_fails(self):
        # `fullmatch` semantics — partial doesn't count
        ok, _ = regex_validator("prefix INV-2026-0001 suffix", r"^INV-\d{4}-\d{4}$")
        assert ok is False

    def test_none_fails(self):
        ok, _ = regex_validator(None, r"^.+$")
        assert ok is False

    def test_invalid_pattern_fails_gracefully(self):
        ok, w = regex_validator("anything", r"[unclosed")
        assert ok is False
        assert "invalid pattern" in (w or "")

    def test_hu_tax_number(self):
        ok, _ = regex_validator("12345678-1-42", r"^\d{8}-\d-\d{2}$")
        assert ok is True


class TestIsoDate:
    def test_iso_string_passes(self):
        ok, _ = iso_date("2026-04-15")
        assert ok is True

    def test_iso_with_time_passes(self):
        ok, _ = iso_date("2026-04-15T13:42:00")
        assert ok is True

    def test_invalid_string_fails(self):
        ok, _ = iso_date("2026/04/15")
        assert ok is False

    def test_none_fails(self):
        ok, _ = iso_date(None)
        assert ok is False

    def test_empty_fails(self):
        ok, _ = iso_date("")
        assert ok is False


class TestBeforeToday:
    def test_yesterday_passes(self):
        yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        ok, _ = before_today(yesterday)
        assert ok is True

    def test_today_fails(self):
        today = datetime.now(UTC).date().isoformat()
        ok, _ = before_today(today)
        assert ok is False

    def test_tomorrow_fails(self):
        tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
        ok, _ = before_today(tomorrow)
        assert ok is False

    def test_invalid_date_fails(self):
        ok, _ = before_today("nonsense")
        assert ok is False


class TestAfterToday:
    def test_tomorrow_passes(self):
        tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
        ok, _ = after_today(tomorrow)
        assert ok is True

    def test_today_fails(self):
        today = datetime.now(UTC).date().isoformat()
        ok, _ = after_today(today)
        assert ok is False

    def test_yesterday_fails(self):
        yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        ok, _ = after_today(yesterday)
        assert ok is False


class TestMinMax:
    def test_min_passes(self):
        ok, _ = min_value(100, 50)
        assert ok is True

    def test_min_equality_passes(self):
        ok, _ = min_value(50, 50)
        assert ok is True

    def test_min_below_fails(self):
        ok, _ = min_value(10, 50)
        assert ok is False

    def test_min_string_numeric_passes(self):
        ok, _ = min_value("100", 50)
        assert ok is True

    def test_min_non_numeric_fails(self):
        ok, _ = min_value("abc", 50)
        assert ok is False

    def test_min_bool_fails(self):
        # True == 1 numerically — but the contract rejects bool
        ok, _ = min_value(True, 0)
        assert ok is False

    def test_max_passes(self):
        ok, _ = max_value(50, 100)
        assert ok is True

    def test_max_above_fails(self):
        ok, _ = max_value(150, 100)
        assert ok is False

    def test_max_european_decimal(self):
        # "1,5" -> 1.5 (European decimal)
        ok, _ = max_value("1,5", 2.0)
        assert ok is True


class TestApplyValidators:
    def test_all_pass(self):
        warnings = apply_validators(
            "INV-2026-0001",
            ["non_empty", "regex:^INV-\\d{4}-\\d{4}$"],
        )
        assert warnings == []

    def test_one_fails(self):
        warnings = apply_validators(
            "",
            ["non_empty", "regex:.+"],
        )
        assert any("non_empty" in w for w in warnings)

    def test_multiple_fail(self):
        warnings = apply_validators(
            "",
            ["non_empty", "regex:^X$"],
        )
        # Both validators fire on empty input
        assert len(warnings) == 2

    def test_unknown_validator_warns(self):
        warnings = apply_validators("hello", ["unknown_check"])
        assert any("unknown" in w.lower() for w in warnings)

    def test_empty_spec_list_no_warnings(self):
        assert apply_validators("anything", []) == []

    def test_min_with_arg(self):
        warnings = apply_validators(100, ["min:50"])
        assert warnings == []

        warnings = apply_validators(10, ["min:50"])
        assert any("min" in w for w in warnings)

    def test_iso_date_compound(self):
        warnings = apply_validators("2020-01-01", ["iso_date", "before_today"])
        assert warnings == []

    def test_skip_non_string_specs(self):
        # Defensive: list with None entries shouldn't crash
        warnings = apply_validators("hello", ["non_empty", None, ""])  # type: ignore[list-item]
        assert warnings == []

    def test_regex_missing_pattern_warns(self):
        warnings = apply_validators("hello", ["regex:"])
        # `regex:` with empty pattern: full_match("") on "hello" fails → warning surfaces as regex mismatch
        assert len(warnings) >= 1
