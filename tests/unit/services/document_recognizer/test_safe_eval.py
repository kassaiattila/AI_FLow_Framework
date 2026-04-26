"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.safe_eval
    covers:
        - src/aiflow/services/document_recognizer/safe_eval.py
    phase: v1.6.0
    priority: critical
    estimated_duration_ms: 40
    requires_services: []
    tags: [unit, services, doc_recognizer, safe_eval, sprint_v, sv_1]
"""

from __future__ import annotations

import pytest

from aiflow.contracts.doc_recognition import DocFieldValue
from aiflow.services.document_recognizer.safe_eval import (
    SafeEvalError,
    safe_eval_intent_rule,
)


def _fields(**kwargs: object) -> dict[str, DocFieldValue]:
    return {name: DocFieldValue(value=val, confidence=0.95) for name, val in kwargs.items()}


class TestSafeEvalBasic:
    def test_extracted_field_compare_truthy(self):
        result = safe_eval_intent_rule(
            "extracted.total_gross > 1000000",
            _fields(total_gross=1500000),
            doc_type_confidence=0.9,
        )
        assert result is True

    def test_extracted_field_compare_falsy(self):
        result = safe_eval_intent_rule(
            "extracted.total_gross > 1000000",
            _fields(total_gross=500000),
            doc_type_confidence=0.9,
        )
        assert result is False

    def test_field_confidence_min(self):
        fields = {
            "a": DocFieldValue(value="x", confidence=0.95),
            "b": DocFieldValue(value="y", confidence=0.4),
        }
        # min == 0.4, rule fires
        assert safe_eval_intent_rule("field_confidence_min < 0.6", fields, 0.9) is True
        # min == 0.4, rule does NOT fire when threshold too low
        assert safe_eval_intent_rule("field_confidence_min < 0.3", fields, 0.9) is False

    def test_doc_type_confidence(self):
        assert safe_eval_intent_rule("doc_type_confidence < 0.85", {}, 0.7) is True
        assert safe_eval_intent_rule("doc_type_confidence < 0.85", {}, 0.95) is False

    def test_pii_detected_flag(self):
        assert safe_eval_intent_rule("pii_detected", {}, 1.0, pii_detected=True) is True
        assert safe_eval_intent_rule("pii_detected", {}, 1.0, pii_detected=False) is False


class TestSafeEvalCompoundExpressions:
    def test_and(self):
        result = safe_eval_intent_rule(
            "extracted.total_gross > 1000000 and doc_type_confidence > 0.9",
            _fields(total_gross=2000000),
            doc_type_confidence=0.95,
        )
        assert result is True

    def test_or(self):
        result = safe_eval_intent_rule(
            "extracted.total_gross > 1000000 or doc_type_confidence < 0.5",
            _fields(total_gross=500000),
            doc_type_confidence=0.4,
        )
        assert result is True

    def test_not(self):
        result = safe_eval_intent_rule(
            "not pii_detected",
            {},
            doc_type_confidence=1.0,
            pii_detected=False,
        )
        assert result is True

    def test_in_membership(self):
        result = safe_eval_intent_rule(
            'extracted.currency in ["EUR", "USD"]',
            _fields(currency="EUR"),
            doc_type_confidence=0.9,
        )
        assert result is True


class TestSafeEvalSecurity:
    def test_dunder_attribute_access_denied(self):
        with pytest.raises(SafeEvalError):
            safe_eval_intent_rule(
                "extracted.__class__",
                _fields(foo=1),
                doc_type_confidence=0.9,
            )

    def test_function_call_denied(self):
        # `len` and other builtins are NOT in the function dict
        with pytest.raises(SafeEvalError):
            safe_eval_intent_rule(
                "len(extracted.value) > 0",
                _fields(value="abc"),
                doc_type_confidence=0.9,
            )

    def test_import_attempt_denied(self):
        with pytest.raises(SafeEvalError):
            safe_eval_intent_rule(
                "__import__('os').system('echo hacked')",
                {},
                doc_type_confidence=0.9,
            )


class TestSafeEvalErrors:
    def test_empty_expr_raises(self):
        with pytest.raises(SafeEvalError, match="non-empty"):
            safe_eval_intent_rule("", {}, 0.9)

    def test_whitespace_expr_raises(self):
        with pytest.raises(SafeEvalError, match="non-empty"):
            safe_eval_intent_rule("   ", {}, 0.9)

    def test_syntax_error_raises(self):
        with pytest.raises(SafeEvalError, match="syntax error"):
            safe_eval_intent_rule(
                "extracted.foo > > 5",
                _fields(foo=1),
                doc_type_confidence=0.9,
            )

    def test_undefined_name_raises(self):
        with pytest.raises(SafeEvalError, match="undefined name"):
            safe_eval_intent_rule(
                "extracted.foo > unknown_variable",
                _fields(foo=10),
                doc_type_confidence=0.9,
            )


class TestSafeEvalEdgeCases:
    def test_missing_field_returns_none_for_strict_check(self):
        """`extracted.foo` for a missing field returns None — comparing with > raises."""
        # Comparison with None raises TypeError under simpleeval -> wrapped as SafeEvalError
        with pytest.raises(SafeEvalError):
            safe_eval_intent_rule(
                "extracted.missing > 100",
                _fields(other=1),
                doc_type_confidence=0.9,
            )

    def test_missing_field_equality_with_none(self):
        """A defensive operator can write `extracted.foo != None and extracted.foo > 100`."""
        assert (
            safe_eval_intent_rule(
                "extracted.foo == None",
                _fields(other=1),
                doc_type_confidence=0.9,
            )
            is True
        )

    def test_no_extracted_fields_field_confidence_default(self):
        """When extracted_fields is empty: min == 1.0 (no failures), max == 0.0."""
        assert safe_eval_intent_rule("field_confidence_min == 1.0", {}, 0.9) is True
        assert safe_eval_intent_rule("field_confidence_max == 0.0", {}, 0.9) is True

    def test_string_equality(self):
        result = safe_eval_intent_rule(
            'extracted.currency == "HUF"',
            _fields(currency="HUF"),
            doc_type_confidence=0.9,
        )
        assert result is True

    def test_plain_dict_fields_also_supported(self):
        """The function accepts plain {field: value} dicts, not just DocFieldValue."""
        # field_confidence_* will default since plain dicts have no .confidence
        result = safe_eval_intent_rule(
            "extracted.x > 5",
            {"x": 10},  # plain dict, value-only
            doc_type_confidence=0.9,
        )
        assert result is True
