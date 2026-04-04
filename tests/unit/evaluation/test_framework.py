"""
@test_registry:
    suite: core-unit
    component: evaluation.framework
    covers: [src/aiflow/evaluation/framework.py]
    phase: 4
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [evaluation, framework, eval-suite, eval-case, scoring]
"""

from typing import Any

import pytest

from aiflow.evaluation.framework import EvalCase, EvalResult, EvalSuite, EvalSummary


class TestEvalCase:
    def test_create_full_case(self):
        case = EvalCase(
            name="test-case-1",
            input_data={"text": "Hello world"},
            expected_output="HELLO WORLD",
            assertions=["exact_match"],
            category="transform",
            tags=["string", "uppercase"],
            priority="high",
        )
        assert case.name == "test-case-1"
        assert case.input_data == {"text": "Hello world"}
        assert case.expected_output == "HELLO WORLD"
        assert "exact_match" in case.assertions
        assert case.category == "transform"
        assert case.priority == "high"

    def test_create_minimal_case(self):
        case = EvalCase(name="minimal", input_data={"x": 1})
        assert case.name == "minimal"
        assert case.expected_output is None
        assert case.assertions == []
        assert case.category == ""
        assert case.tags == []
        assert case.priority == "normal"

    def test_case_defaults(self):
        case = EvalCase(name="defaults", input_data={})
        assert case.expected_output is None
        assert case.assertions == []
        assert case.tags == []


class TestEvalResult:
    def test_result_passed(self):
        result = EvalResult(
            case_name="pass-case",
            passed=True,
            actual_output="result",
            scores={"accuracy": 1.0},
            duration_ms=42.5,
        )
        assert result.passed is True
        assert result.scores["accuracy"] == 1.0
        assert result.error is None

    def test_result_failed_with_error(self):
        result = EvalResult(
            case_name="fail-case",
            passed=False,
            error="Something went wrong",
            duration_ms=10.0,
        )
        assert result.passed is False
        assert result.error == "Something went wrong"
        assert result.actual_output is None

    def test_result_defaults(self):
        result = EvalResult(case_name="def", passed=True)
        assert result.scores == {}
        assert result.duration_ms == 0.0
        assert result.cost_usd == 0.0


class TestEvalSuite:
    @pytest.fixture
    def suite(self) -> EvalSuite:
        return EvalSuite(name="test-suite")

    def test_run_with_passing_cases(self, suite: EvalSuite):
        cases = [
            EvalCase(name="case-1", input_data={"n": 2}),
            EvalCase(name="case-2", input_data={"n": 3}),
        ]

        def double(data: dict[str, Any]) -> int:
            return data["n"] * 2

        results = suite.run(cases, double)
        assert len(results) == 2
        assert all(r.passed for r in results)
        assert results[0].actual_output == 4
        assert results[1].actual_output == 6

    def test_run_with_assertion_scorer(self, suite: EvalSuite):
        cases = [
            EvalCase(
                name="scored",
                input_data={"text": "hello"},
                expected_output="hello",
                assertions=["exact_match"],
            ),
        ]

        def identity(data: dict[str, Any]) -> str:
            return data["text"]

        def exact_scorer(actual: Any, expected: Any) -> tuple[float, bool]:
            return (1.0, True) if actual == expected else (0.0, False)

        results = suite.run(cases, identity, scorers={"exact_match": exact_scorer})
        assert results[0].passed is True
        assert results[0].scores["exact_match"] == 1.0

    def test_run_with_failing_assertion(self, suite: EvalSuite):
        cases = [
            EvalCase(
                name="fails",
                input_data={"text": "hello"},
                expected_output="world",
                assertions=["exact_match"],
            ),
        ]

        def identity(data: dict[str, Any]) -> str:
            return data["text"]

        def exact_scorer(actual: Any, expected: Any) -> tuple[float, bool]:
            return (1.0, True) if actual == expected else (0.0, False)

        results = suite.run(cases, identity, scorers={"exact_match": exact_scorer})
        assert results[0].passed is False
        assert results[0].scores["exact_match"] == 0.0

    def test_run_captures_exception(self, suite: EvalSuite):
        cases = [EvalCase(name="error-case", input_data={"x": 1})]

        def broken(data: dict[str, Any]) -> None:
            raise RuntimeError("boom")

        results = suite.run(cases, broken)
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].error == "boom"
        assert results[0].duration_ms > 0

    def test_run_records_duration(self, suite: EvalSuite):
        cases = [EvalCase(name="timed", input_data={})]

        def noop(data: dict[str, Any]) -> str:
            return "ok"

        results = suite.run(cases, noop)
        assert results[0].duration_ms >= 0


class TestEvalSummary:
    def test_summary_all_pass(self):
        results = [
            EvalResult(case_name="a", passed=True, duration_ms=10),
            EvalResult(case_name="b", passed=True, duration_ms=20),
        ]
        s = EvalSuite.summary(results)
        assert s.total == 2
        assert s.passed == 2
        assert s.failed == 0
        assert s.pass_rate == 1.0
        assert s.total_duration_ms == 30.0
        assert s.avg_duration_ms == 15.0

    def test_summary_mixed_results(self):
        results = [
            EvalResult(case_name="a", passed=True, duration_ms=10, cost_usd=0.01),
            EvalResult(case_name="b", passed=False, error="err", duration_ms=5),
        ]
        s = EvalSuite.summary(results)
        assert s.total == 2
        assert s.passed == 1
        assert s.failed == 1
        assert s.error_count == 1
        assert s.pass_rate == 0.5
        assert s.total_cost_usd == 0.01

    def test_summary_empty(self):
        s = EvalSuite.summary([])
        assert s.total == 0
        assert s.pass_rate == 0.0
        assert isinstance(s, EvalSummary)
