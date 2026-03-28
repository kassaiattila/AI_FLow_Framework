"""
@test_registry:
    suite: agents-unit
    component: agents.quality_gate
    covers: [src/aiflow/agents/quality_gate.py]
    phase: 3
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [agents, quality_gate, scoring, threshold, evaluation]
"""
import pytest

from aiflow.agents.quality_gate import QualityGate, QualityGateResult, OnFailAction


class TestQualityGatePass:
    def test_passes_when_score_above_threshold(self):
        gate = QualityGate(name="acc_check", metric="accuracy", threshold=0.8)
        result = gate.evaluate({"accuracy": 0.95})
        assert result.passed is True

    def test_passes_when_score_equals_threshold(self):
        gate = QualityGate(name="acc_check", metric="accuracy", threshold=0.8)
        result = gate.evaluate({"accuracy": 0.8})
        assert result.passed is True

    def test_passes_with_perfect_score(self):
        gate = QualityGate(name="q_check", metric="quality", threshold=0.5)
        result = gate.evaluate({"quality": 1.0})
        assert result.passed is True


class TestQualityGateFail:
    def test_fails_when_score_below_threshold(self):
        gate = QualityGate(name="acc_check", metric="accuracy", threshold=0.8)
        result = gate.evaluate({"accuracy": 0.5})
        assert result.passed is False

    def test_fails_with_zero_score(self):
        gate = QualityGate(name="acc_check", metric="accuracy", threshold=0.1)
        result = gate.evaluate({"accuracy": 0.0})
        assert result.passed is False


class TestOnFailAction:
    def test_on_fail_retry(self):
        gate = QualityGate(name="g1", metric="accuracy", threshold=0.8, on_fail=OnFailAction.RETRY)
        assert gate.on_fail == "retry"

    def test_on_fail_escalate(self):
        gate = QualityGate(
            name="g2", metric="accuracy", threshold=0.8, on_fail=OnFailAction.ESCALATE
        )
        assert gate.on_fail == "escalate"

    def test_on_fail_reject(self):
        gate = QualityGate(
            name="g3", metric="accuracy", threshold=0.8, on_fail=OnFailAction.REJECT
        )
        assert gate.on_fail == "reject"

    def test_on_fail_human_review(self):
        gate = QualityGate(
            name="g4", metric="accuracy", threshold=0.8, on_fail=OnFailAction.HUMAN_REVIEW
        )
        assert gate.on_fail == "human_review"

    def test_failed_result_carries_action_taken(self):
        gate = QualityGate(
            name="esc_gate", metric="accuracy", threshold=0.9, on_fail=OnFailAction.ESCALATE
        )
        result = gate.evaluate({"accuracy": 0.5})
        assert result.passed is False
        assert result.action_taken == "escalate"

    def test_passed_result_action_taken_is_none(self):
        gate = QualityGate(
            name="pass_gate", metric="accuracy", threshold=0.5, on_fail=OnFailAction.REJECT
        )
        result = gate.evaluate({"accuracy": 0.9})
        assert result.passed is True
        assert result.action_taken is None


class TestQualityGateDefaults:
    def test_default_threshold(self):
        gate = QualityGate(name="def_gate", metric="accuracy")
        assert gate.threshold == 0.5

    def test_default_on_fail(self):
        gate = QualityGate(name="def_gate", metric="accuracy")
        assert gate.on_fail == OnFailAction.RETRY

    def test_default_max_retries(self):
        gate = QualityGate(name="def_gate", metric="accuracy")
        assert gate.max_retries == 2


class TestQualityGateResult:
    def test_result_passed(self):
        result = QualityGateResult(
            passed=True, metric_value=0.95, gate_name="acc_check"
        )
        assert result.passed is True
        assert result.metric_value == 0.95
        assert result.gate_name == "acc_check"
        assert result.action_taken is None

    def test_result_failed_with_action(self):
        result = QualityGateResult(
            passed=False,
            metric_value=0.5,
            gate_name="acc_check",
            action_taken="retry",
        )
        assert result.passed is False
        assert result.action_taken == "retry"


class TestMultipleGates:
    def test_evaluate_multiple_gates(self):
        gates = [
            QualityGate(name="gate_acc", metric="accuracy", threshold=0.8),
            QualityGate(name="gate_rel", metric="relevance", threshold=0.7),
        ]
        scores = {"accuracy": 0.9, "relevance": 0.85}
        results = [g.evaluate(scores) for g in gates]
        assert all(r.passed for r in results)

    def test_partial_failure_across_gates(self):
        gates = [
            QualityGate(name="gate_acc", metric="accuracy", threshold=0.8),
            QualityGate(name="gate_rel", metric="relevance", threshold=0.9),
        ]
        scores = {"accuracy": 0.85, "relevance": 0.5}
        results = [g.evaluate(scores) for g in gates]
        assert results[0].passed is True
        assert results[1].passed is False


class TestMissingMetric:
    def test_missing_metric_fails_with_negative_value(self):
        gate = QualityGate(name="miss_gate", metric="accuracy", threshold=0.8)
        result = gate.evaluate({"relevance": 0.9})
        assert result.passed is False
        assert result.metric_value == -1.0

    def test_empty_scores_fails(self):
        gate = QualityGate(name="empty_gate", metric="accuracy", threshold=0.5)
        result = gate.evaluate({})
        assert result.passed is False
        assert result.metric_value == -1.0


class TestThresholdEdgeCases:
    def test_threshold_zero(self):
        gate = QualityGate(name="zero_gate", metric="x", threshold=0.0)
        result = gate.evaluate({"x": 0.0})
        assert result.passed is True

    def test_threshold_one(self):
        gate = QualityGate(name="one_gate", metric="x", threshold=1.0)
        result = gate.evaluate({"x": 1.0})
        assert result.passed is True

    def test_just_below_threshold(self):
        gate = QualityGate(name="below_gate", metric="x", threshold=0.8)
        result = gate.evaluate({"x": 0.7999})
        assert result.passed is False

    def test_result_gate_name_matches(self):
        gate = QualityGate(name="my_gate", metric="x", threshold=0.5)
        result = gate.evaluate({"x": 0.6})
        assert result.gate_name == "my_gate"
