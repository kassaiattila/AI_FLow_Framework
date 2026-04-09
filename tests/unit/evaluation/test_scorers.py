"""
@test_registry:
    suite: core-unit
    component: evaluation.scorers
    covers: [src/aiflow/evaluation/scorers.py]
    phase: 4
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [evaluation, scorers, exact-match, json, regex, threshold]
"""

import json

from aiflow.evaluation.scorers import (
    contains,
    exact_match,
    json_field_equals,
    json_valid,
    regex_match,
    threshold_check,
)


class TestExactMatch:
    def test_equal_strings(self):
        score, passed = exact_match("hello", "hello")
        assert score == 1.0
        assert passed is True

    def test_unequal_strings(self):
        score, passed = exact_match("hello", "world")
        assert score == 0.0
        assert passed is False

    def test_equal_numbers(self):
        score, passed = exact_match(42, 42)
        assert score == 1.0
        assert passed is True

    def test_equal_dicts(self):
        score, passed = exact_match({"a": 1}, {"a": 1})
        assert score == 1.0
        assert passed is True

    def test_none_values(self):
        score, passed = exact_match(None, None)
        assert passed is True


class TestContains:
    def test_substring_present(self):
        score, passed = contains("hello world", "world")
        assert score == 1.0
        assert passed is True

    def test_substring_absent(self):
        score, passed = contains("hello", "world")
        assert score == 0.0
        assert passed is False

    def test_numeric_conversion(self):
        score, passed = contains("value is 42", "42")
        assert passed is True


class TestJsonValid:
    def test_valid_dict(self):
        score, passed = json_valid({"key": "value"})
        assert passed is True

    def test_valid_list(self):
        score, passed = json_valid([1, 2, 3])
        assert passed is True

    def test_valid_json_string(self):
        score, passed = json_valid('{"key": "value"}')
        assert passed is True

    def test_invalid_json_string(self):
        score, passed = json_valid("not json at all")
        assert passed is False
        assert score == 0.0


class TestJsonFieldEquals:
    def test_simple_field_match(self):
        data = {"status": "ok"}
        score, passed = json_field_equals(data, field="status", value="ok")
        assert passed is True
        assert score == 1.0

    def test_nested_field_match(self):
        data = {"result": {"code": 200}}
        score, passed = json_field_equals(data, field="result.code", value=200)
        assert passed is True

    def test_field_mismatch(self):
        data = {"status": "error"}
        score, passed = json_field_equals(data, field="status", value="ok")
        assert passed is False
        assert score == 0.0

    def test_missing_field(self):
        data = {"other": "value"}
        score, passed = json_field_equals(data, field="status", value="ok")
        assert passed is False

    def test_json_string_input(self):
        data = json.dumps({"name": "test"})
        score, passed = json_field_equals(data, field="name", value="test")
        assert passed is True


class TestThresholdCheck:
    def test_within_range(self):
        score, passed = threshold_check(0.8, min_value=0.0, max_value=1.0)
        assert passed is True
        assert score == 1.0

    def test_below_minimum(self):
        score, passed = threshold_check(-1.0, min_value=0.0, max_value=1.0)
        assert passed is False

    def test_above_maximum(self):
        score, passed = threshold_check(2.0, min_value=0.0, max_value=1.0)
        assert passed is False

    def test_min_only(self):
        score, passed = threshold_check(5, min_value=3)
        assert passed is True

    def test_max_only(self):
        score, passed = threshold_check(5, max_value=10)
        assert passed is True

    def test_non_numeric_fails(self):
        score, passed = threshold_check("not-a-number", min_value=0)
        assert passed is False
        assert score == 0.0


class TestRegexMatch:
    def test_pattern_matches(self):
        score, passed = regex_match("error code 404", pattern=r"error code \d+")
        assert passed is True
        assert score == 1.0

    def test_pattern_no_match(self):
        score, passed = regex_match("all good", pattern=r"error")
        assert passed is False
        assert score == 0.0

    def test_expected_as_pattern(self):
        score, passed = regex_match("hello123", r"\w+\d+")
        assert passed is True

    def test_empty_pattern(self):
        score, passed = regex_match("anything")
        assert passed is False

    def test_invalid_regex(self):
        score, passed = regex_match("test", pattern="[invalid")
        assert passed is False
