"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.classifier
    covers:
        - src/aiflow/services/document_recognizer/classifier.py
    phase: v1.6.0
    priority: critical
    estimated_duration_ms: 60
    requires_services: []
    tags: [unit, services, doc_recognizer, classifier, sprint_v, sv_2]
"""

from __future__ import annotations

from aiflow.contracts.doc_recognition import (
    DocTypeDescriptor,
    ExtractionConfig,
    FieldSpec,
    RuleSpec,
    TypeClassifierConfig,
)
from aiflow.services.document_recognizer.classifier import (
    ClassifierInput,
    RuleEngine,
    classify_doctype,
    needs_llm_fallback,
)


def _descriptor(
    name: str = "hu_invoice",
    rules: list[RuleSpec] | None = None,
    *,
    llm_fallback: bool = True,
    threshold: float = 0.7,
) -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name=name,
        display_name=f"Display {name}",
        type_classifier=TypeClassifierConfig(
            rules=rules or [],
            llm_fallback=llm_fallback,
            llm_threshold_below=threshold,
        ),
        extraction=ExtractionConfig(
            workflow=f"{name}_extraction_chain",
            fields=[FieldSpec(name="x", type="string", required=True)],
        ),
    )


# ---------------------------------------------------------------------------
# Per-rule kind
# ---------------------------------------------------------------------------


class TestRuleKindRegex:
    def test_match_truthy(self):
        d = _descriptor(rules=[RuleSpec(kind="regex", weight=0.5, pattern=r"\bSzámla\b")])
        ctx = ClassifierInput(text="Ez egy Számla 2026")
        assert RuleEngine().score_descriptor(d, ctx) == 0.5

    def test_match_falsy(self):
        d = _descriptor(rules=[RuleSpec(kind="regex", weight=0.5, pattern=r"\bSzámla\b")])
        ctx = ClassifierInput(text="Levelünk tárgya: meeting")
        assert RuleEngine().score_descriptor(d, ctx) == 0.0

    def test_case_insensitive(self):
        d = _descriptor(rules=[RuleSpec(kind="regex", weight=0.3, pattern=r"szamla")])
        ctx = ClassifierInput(text="SZAMLA 12345")
        assert RuleEngine().score_descriptor(d, ctx) == 0.3

    def test_invalid_regex_returns_zero(self):
        d = _descriptor(rules=[RuleSpec(kind="regex", weight=0.5, pattern=r"[unclosed")])
        ctx = ClassifierInput(text="anything")
        # Bad regex logs warning and returns 0 — never crashes the pipeline
        assert RuleEngine().score_descriptor(d, ctx) == 0.0


class TestRuleKindKeywordList:
    def test_threshold_met(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="keyword_list",
                    weight=0.4,
                    keywords=["nettó", "bruttó", "ÁFA"],
                    threshold=2,
                )
            ]
        )
        ctx = ClassifierInput(text="A nettó ár 10000, az ÁFA 27%")
        # 2 hits met the threshold of 2
        assert RuleEngine().score_descriptor(d, ctx) == 0.4

    def test_threshold_not_met(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="keyword_list",
                    weight=0.4,
                    keywords=["nettó", "bruttó", "ÁFA"],
                    threshold=2,
                )
            ]
        )
        ctx = ClassifierInput(text="Csak a nettó szerepel")
        # 1 hit < threshold 2
        assert RuleEngine().score_descriptor(d, ctx) == 0.0

    def test_case_insensitive(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="keyword_list",
                    weight=0.3,
                    keywords=["INVOICE"],
                    threshold=1,
                )
            ]
        )
        ctx = ClassifierInput(text="this is an invoice document")
        assert RuleEngine().score_descriptor(d, ctx) == 0.3


class TestRuleKindStructureHint:
    def test_table_count_gte(self):
        d = _descriptor(
            rules=[RuleSpec(kind="structure_hint", weight=0.2, hint="table_count >= 1")]
        )
        ctx = ClassifierInput(text="x", table_count=2)
        assert RuleEngine().score_descriptor(d, ctx) == 0.2

    def test_page_count_eq_1(self):
        d = _descriptor(rules=[RuleSpec(kind="structure_hint", weight=0.1, hint="page_count == 1")])
        ctx = ClassifierInput(text="x", page_count=1)
        assert RuleEngine().score_descriptor(d, ctx) == 0.1

        ctx = ClassifierInput(text="x", page_count=3)
        assert RuleEngine().score_descriptor(d, ctx) == 0.0

    def test_unknown_var_returns_zero(self):
        d = _descriptor(
            rules=[RuleSpec(kind="structure_hint", weight=0.5, hint="unknown_var == 42")]
        )
        ctx = ClassifierInput(text="x")
        assert RuleEngine().score_descriptor(d, ctx) == 0.0


class TestRuleKindFilenameMatch:
    def test_match(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="filename_match",
                    weight=0.05,
                    pattern=r"^szamla_.*\.pdf$",
                )
            ]
        )
        ctx = ClassifierInput(text="x", filename="szamla_2026_001.pdf")
        assert RuleEngine().score_descriptor(d, ctx) == 0.05

    def test_no_filename_returns_zero(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="filename_match",
                    weight=0.05,
                    pattern=r"^szamla_.*\.pdf$",
                )
            ]
        )
        ctx = ClassifierInput(text="x", filename=None)
        assert RuleEngine().score_descriptor(d, ctx) == 0.0


class TestRuleKindParserMetadata:
    def test_mime_type_match(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="parser_metadata",
                    weight=0.1,
                    hint="mime_type == application/pdf",
                )
            ]
        )
        ctx = ClassifierInput(text="x", mime_type="application/pdf")
        assert RuleEngine().score_descriptor(d, ctx) == 0.1

        ctx = ClassifierInput(text="x", mime_type="image/jpeg")
        assert RuleEngine().score_descriptor(d, ctx) == 0.0

    def test_parser_used_match(self):
        d = _descriptor(
            rules=[
                RuleSpec(
                    kind="parser_metadata",
                    weight=0.1,
                    hint="parser_used == azure_di",
                )
            ]
        )
        ctx = ClassifierInput(text="x", parser_used="azure_di")
        assert RuleEngine().score_descriptor(d, ctx) == 0.1


# ---------------------------------------------------------------------------
# classify_doctype + needs_llm_fallback
# ---------------------------------------------------------------------------


class TestClassifyDoctype:
    def test_no_descriptors_returns_none(self):
        ctx = ClassifierInput(text="x")
        assert classify_doctype([], ctx) is None

    def test_no_rules_match_returns_none(self):
        d = _descriptor(rules=[RuleSpec(kind="regex", weight=0.5, pattern=r"\bSzámla\b")])
        ctx = ClassifierInput(text="meeting agenda for next week")
        assert classify_doctype([d], ctx) is None

    def test_single_descriptor_match(self):
        d = _descriptor(
            rules=[
                RuleSpec(kind="regex", weight=0.5, pattern=r"\bSzámla\b"),
                RuleSpec(kind="structure_hint", weight=0.5, hint="table_count >= 1"),
            ]
        )
        ctx = ClassifierInput(text="Ez egy Számla...", table_count=2)
        match = classify_doctype([d], ctx)
        assert match is not None
        assert match.doc_type == "hu_invoice"
        assert match.confidence == 1.0  # both rules fired, sum=1.0, normalized=1.0

    def test_two_descriptors_top_1_picked(self):
        invoice = _descriptor(
            name="hu_invoice",
            rules=[
                RuleSpec(kind="regex", weight=0.5, pattern=r"\bSzámla\b"),
                RuleSpec(kind="keyword_list", weight=0.5, keywords=["nettó"], threshold=1),
            ],
        )
        id_card = _descriptor(
            name="hu_id_card",
            rules=[
                RuleSpec(kind="regex", weight=0.5, pattern=r"MAGYARORSZÁG"),
                RuleSpec(kind="regex", weight=0.5, pattern=r"\b\d{6}[A-Z]{2}\b"),
            ],
        )
        ctx = ClassifierInput(text="Számla — nettó ár 10000")
        match = classify_doctype([invoice, id_card], ctx)
        assert match is not None
        assert match.doc_type == "hu_invoice"
        # id_card scored 0 — alternatives drops it
        assert match.alternatives == []

    def test_alternatives_top_k(self):
        a = _descriptor(
            name="a",
            rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"\bX\b")],
        )
        b = _descriptor(
            name="b",
            rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"\bX\b")],  # both score 1.0
        )
        ctx = ClassifierInput(text="X is here")
        match = classify_doctype([a, b], ctx, top_k=2)
        assert match is not None
        # Top-1 is `a` (stable sort), `b` lands in alternatives
        assert match.doc_type == "a"
        assert match.alternatives == [("b", 1.0)]


class TestNeedsLlmFallback:
    def test_no_match_needs_fallback(self):
        d = _descriptor()
        assert needs_llm_fallback(None, d) is True

    def test_no_descriptor_needs_fallback(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        m = DocTypeMatch(doc_type="hu_invoice", confidence=0.9)
        assert needs_llm_fallback(m, None) is True

    def test_high_confidence_no_fallback(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        d = _descriptor(threshold=0.7, llm_fallback=True)
        m = DocTypeMatch(doc_type="hu_invoice", confidence=0.85)
        assert needs_llm_fallback(m, d) is False

    def test_below_threshold_triggers_fallback(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        d = _descriptor(threshold=0.7, llm_fallback=True)
        m = DocTypeMatch(doc_type="hu_invoice", confidence=0.55)
        assert needs_llm_fallback(m, d) is True

    def test_fallback_disabled_descriptor(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        d = _descriptor(threshold=0.7, llm_fallback=False)
        m = DocTypeMatch(doc_type="hu_invoice", confidence=0.3)
        # Even with low confidence, descriptor opted out of LLM fallback
        assert needs_llm_fallback(m, d) is False
