"""
@test_registry:
    suite: engine-unit
    component: engine.conditions
    covers: [src/aiflow/engine/conditions.py]
    phase: 2
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [engine, conditions, branching, expressions]
"""
from aiflow.engine.conditions import Condition, evaluate_condition


class TestEvaluateCondition:
    def test_string_equality(self):
        assert evaluate_condition("output.category == 'process'", {"category": "process"}) is True

    def test_string_inequality(self):
        assert evaluate_condition("output.category == 'process'", {"category": "greeting"}) is False

    def test_numeric_greater_or_equal(self):
        assert evaluate_condition("output.score >= 8", {"score": 8}) is True
        assert evaluate_condition("output.score >= 8", {"score": 9}) is True
        assert evaluate_condition("output.score >= 8", {"score": 7}) is False

    def test_numeric_less_than(self):
        assert evaluate_condition("output.confidence < 0.5", {"confidence": 0.3}) is True
        assert evaluate_condition("output.confidence < 0.5", {"confidence": 0.8}) is False

    def test_not_equal(self):
        assert evaluate_condition("output.status != 'error'", {"status": "ok"}) is True

    def test_boolean(self):
        assert evaluate_condition("output.valid == true", {"valid": True}) is True
        assert evaluate_condition("output.valid == false", {"valid": False}) is True

    def test_nested_path(self):
        data = {"result": {"category": "process"}}
        assert evaluate_condition("output.result.category == 'process'", data) is True

    def test_missing_field_returns_false(self):
        assert evaluate_condition("output.missing == 'value'", {"other": "data"}) is False

    def test_invalid_expression_returns_false(self):
        assert evaluate_condition("invalid expression", {}) is False

    def test_float_comparison(self):
        assert evaluate_condition("output.score >= 0.8", {"score": 0.85}) is True

    def test_double_quoted_string(self):
        assert evaluate_condition('output.name == "John"', {"name": "John"}) is True


class TestConditionModel:
    def test_condition_evaluate(self):
        cond = Condition(expression="output.score >= 0.8", target_steps=["generate"])
        assert cond.evaluate({"score": 0.9}) is True
        assert cond.evaluate({"score": 0.5}) is False

    def test_condition_target_steps(self):
        cond = Condition(expression="output.x == 1", target_steps=["step_a", "step_b"])
        assert cond.target_steps == ["step_a", "step_b"]
