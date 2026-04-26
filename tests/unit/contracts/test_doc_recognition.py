"""
@test_registry:
    suite: core-unit
    component: contracts.doc_recognition
    covers:
        - src/aiflow/contracts/doc_recognition.py
    phase: v1.6.0
    priority: critical
    estimated_duration_ms: 80
    requires_services: []
    tags: [unit, contracts, doc_recognition, sprint_v, sv_1]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,
    DocIntentDecision,
    DocRecognitionRequest,
    DocTypeDescriptor,
    DocTypeMatch,
    ExtractionConfig,
    FieldSpec,
    IntentRoutingConfig,
    IntentRoutingRule,
    RuleSpec,
    TypeClassifierConfig,
)

# ---------------------------------------------------------------------------
# DocRecognitionRequest
# ---------------------------------------------------------------------------


class TestDocRecognitionRequest:
    def test_with_file_path(self):
        r = DocRecognitionRequest(file_path=Path("/tmp/test.pdf"), tenant_id="t1")
        assert r.tenant_id == "t1"
        assert r.file_path == Path("/tmp/test.pdf")

    def test_with_file_bytes(self):
        r = DocRecognitionRequest(file_bytes=b"%PDF-1.4...", tenant_id="t1")
        assert r.file_bytes == b"%PDF-1.4..."

    def test_neither_source_raises(self):
        with pytest.raises(ValueError, match="at least one of file_path / file_bytes"):
            DocRecognitionRequest(tenant_id="t1")

    def test_round_trip_json(self):
        r = DocRecognitionRequest(
            file_path=Path("/tmp/x.pdf"),
            tenant_id="acme",
            doc_type_hint="hu_invoice",
            filename="szamla.pdf",
        )
        d = r.model_dump(mode="json")
        r2 = DocRecognitionRequest.model_validate(d)
        assert r2.tenant_id == r.tenant_id
        assert r2.doc_type_hint == r.doc_type_hint
        assert r2.filename == r.filename


# ---------------------------------------------------------------------------
# DocTypeMatch
# ---------------------------------------------------------------------------


class TestDocTypeMatch:
    def test_basic(self):
        m = DocTypeMatch(doc_type="hu_invoice", confidence=0.85)
        assert m.alternatives == []

    def test_with_alternatives(self):
        m = DocTypeMatch(
            doc_type="hu_invoice",
            confidence=0.7,
            alternatives=[("pdf_contract", 0.18), ("hu_address_card", 0.05)],
        )
        assert len(m.alternatives) == 2

    def test_too_many_alternatives_raises(self):
        with pytest.raises(ValueError, match="at most 3"):
            DocTypeMatch(
                doc_type="hu_invoice",
                confidence=0.5,
                alternatives=[("a", 0.1), ("b", 0.1), ("c", 0.1), ("d", 0.1)],
            )

    def test_alternative_bad_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence must be in"):
            DocTypeMatch(
                doc_type="hu_invoice",
                confidence=0.5,
                alternatives=[("pdf_contract", 1.5)],
            )

    def test_round_trip_json(self):
        m = DocTypeMatch(
            doc_type="hu_id_card", confidence=0.92, alternatives=[("eu_passport", 0.07)]
        )
        d = m.model_dump(mode="json")
        m2 = DocTypeMatch.model_validate(d)
        assert m2.doc_type == m.doc_type
        # JSON round-trip turns tuples into lists; that's expected.
        assert list(m2.alternatives[0]) == list(m.alternatives[0])


# ---------------------------------------------------------------------------
# DocFieldValue + DocExtractionResult
# ---------------------------------------------------------------------------


class TestDocFieldValue:
    def test_string_value(self):
        f = DocFieldValue(value="INV-2026-0001", confidence=0.95)
        assert f.value == "INV-2026-0001"

    def test_numeric_value(self):
        f = DocFieldValue(value=12345, confidence=0.8)
        assert f.value == 12345

    def test_default_none(self):
        f = DocFieldValue()
        assert f.value is None
        assert f.confidence == 0.0


class TestDocExtractionResult:
    def test_round_trip_json(self):
        r = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={
                "invoice_number": DocFieldValue(value="INV-1", confidence=0.95),
                "total_gross": DocFieldValue(value=12500, confidence=0.88),
            },
            cost_usd=0.0042,
            extraction_time_ms=245.3,
        )
        d = r.model_dump(mode="json")
        r2 = DocExtractionResult.model_validate(d)
        assert r2.doc_type == "hu_invoice"
        assert r2.extracted_fields["invoice_number"].value == "INV-1"
        assert r2.cost_usd == pytest.approx(0.0042)


# ---------------------------------------------------------------------------
# DocIntentDecision
# ---------------------------------------------------------------------------


class TestDocIntentDecision:
    def test_process_default(self):
        d = DocIntentDecision(intent="process")
        assert d.intent == "process"

    def test_route_to_human(self):
        d = DocIntentDecision(
            intent="route_to_human",
            reason="Magas összegű számla — kötelező manuális ellenőrzés",
        )
        assert d.intent == "route_to_human"
        assert "manuális" in d.reason

    def test_invalid_intent_raises(self):
        with pytest.raises(ValueError):
            DocIntentDecision(intent="archive")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# RuleSpec
# ---------------------------------------------------------------------------


class TestRuleSpec:
    def test_regex_requires_pattern(self):
        with pytest.raises(ValueError, match="kind='regex'"):
            RuleSpec(kind="regex", weight=0.3)

    def test_regex_with_pattern_ok(self):
        r = RuleSpec(kind="regex", weight=0.3, pattern=r"\bSzámla\b")
        assert r.pattern == r"\bSzámla\b"

    def test_keyword_list_requires_keywords_and_threshold(self):
        with pytest.raises(ValueError, match="keyword_list"):
            RuleSpec(kind="keyword_list", weight=0.2)

    def test_keyword_list_complete_ok(self):
        r = RuleSpec(
            kind="keyword_list",
            weight=0.25,
            keywords=["nettó", "bruttó", "ÁFA"],
            threshold=2,
        )
        assert r.threshold == 2

    def test_structure_hint_requires_hint(self):
        with pytest.raises(ValueError, match="structure_hint"):
            RuleSpec(kind="structure_hint", weight=0.1)

    def test_filename_match_requires_pattern(self):
        with pytest.raises(ValueError, match="filename_match"):
            RuleSpec(kind="filename_match", weight=0.05)

    def test_parser_metadata_requires_hint(self):
        with pytest.raises(ValueError, match="parser_metadata"):
            RuleSpec(kind="parser_metadata", weight=0.05)

    def test_weight_out_of_range_raises(self):
        with pytest.raises(ValueError):
            RuleSpec(kind="regex", weight=1.5, pattern=r"\d+")

    def test_round_trip_json(self):
        r = RuleSpec(
            kind="regex",
            weight=0.35,
            pattern=r"\bSzámlaszám\b",
        )
        d = r.model_dump(mode="json")
        r2 = RuleSpec.model_validate(d)
        assert r2.kind == r.kind
        assert r2.weight == pytest.approx(r.weight)


# ---------------------------------------------------------------------------
# IntentRoutingRule
# ---------------------------------------------------------------------------


class TestIntentRoutingRule:
    def test_basic(self):
        r = IntentRoutingRule(
            if_expr="extracted.total_gross > 1000000",
            intent="route_to_human",
            reason="Magas összeg",
        )
        assert r.if_expr.startswith("extracted.")

    def test_yaml_alias_if(self):
        """YAML descriptors use ``if`` (Python keyword), the model accepts via alias."""
        r = IntentRoutingRule.model_validate(
            {"if": "doc_type_confidence < 0.75", "intent": "reject", "reason": "too uncertain"}
        )
        assert r.intent == "reject"
        assert r.if_expr == "doc_type_confidence < 0.75"


# ---------------------------------------------------------------------------
# DocTypeDescriptor (full round-trip)
# ---------------------------------------------------------------------------


class TestDocTypeDescriptor:
    def _full_descriptor(self) -> DocTypeDescriptor:
        return DocTypeDescriptor(
            name="hu_invoice",
            display_name="Magyar számla",
            description="HU ÁFA-tartalmú számla",
            language="hu",
            category="financial",
            version=1,
            pii_level="low",
            parser_preferences=["docling", "azure_di", "unstructured"],
            type_classifier=TypeClassifierConfig(
                rules=[
                    RuleSpec(kind="regex", weight=0.35, pattern=r"\bSzámla\s*sz[aá]m\b"),
                    RuleSpec(
                        kind="keyword_list",
                        weight=0.30,
                        keywords=["nettó", "bruttó", "ÁFA"],
                        threshold=2,
                    ),
                    RuleSpec(kind="structure_hint", weight=0.10, hint="table_count >= 1"),
                ],
                llm_fallback=True,
                llm_threshold_below=0.7,
            ),
            extraction=ExtractionConfig(
                workflow="invoice_extraction_chain",
                fields=[
                    FieldSpec(name="invoice_number", type="string", required=True),
                    FieldSpec(name="issue_date", type="date", required=True),
                    FieldSpec(name="total_gross", type="money", required=True),
                ],
            ),
            intent_routing=IntentRoutingConfig(
                default="process",
                conditions=[
                    IntentRoutingRule(
                        if_expr="extracted.total_gross > 1000000",
                        intent="route_to_human",
                        reason="Magas összeg",
                    )
                ],
            ),
        )

    def test_construct_full_descriptor(self):
        d = self._full_descriptor()
        assert d.name == "hu_invoice"
        assert d.field_names() == ["invoice_number", "issue_date", "total_gross"]

    def test_total_rule_weight(self):
        d = self._full_descriptor()
        assert d.total_rule_weight() == pytest.approx(0.75)

    def test_round_trip_json(self):
        d = self._full_descriptor()
        payload = d.model_dump(mode="json")
        d2 = DocTypeDescriptor.model_validate(payload)
        assert d2.name == d.name
        assert d2.field_names() == d.field_names()
        assert d2.intent_routing.conditions[0].intent == "route_to_human"

    def test_invalid_name_pattern_raises(self):
        with pytest.raises(ValueError):
            DocTypeDescriptor(
                name="HU-Invoice",  # uppercase + hyphen disallowed by regex
                display_name="HU",
                type_classifier=TypeClassifierConfig(rules=[]),
                extraction=ExtractionConfig(workflow="x"),
            )

    def test_dump_yaml_safe_drops_created_at(self):
        d = self._full_descriptor()
        payload = d.model_dump_yaml_safe()
        assert "created_at" not in payload
        # `if` alias preserved for IntentRoutingRule
        assert payload["intent_routing"]["conditions"][0]["if"] == "extracted.total_gross > 1000000"
