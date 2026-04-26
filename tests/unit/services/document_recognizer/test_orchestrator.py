"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.orchestrator
    covers:
        - src/aiflow/services/document_recognizer/orchestrator.py
    phase: v1.6.0
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [unit, services, doc_recognizer, orchestrator, sprint_v, sv_2]
"""

from __future__ import annotations

import pytest

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,
    DocTypeDescriptor,
    ExtractionConfig,
    FieldSpec,
    IntentRoutingConfig,
    IntentRoutingRule,
    RuleSpec,
    TypeClassifierConfig,
)
from aiflow.services.document_recognizer.classifier import ClassifierInput
from aiflow.services.document_recognizer.orchestrator import (
    DocumentRecognizerOrchestrator,
)
from aiflow.services.document_recognizer.registry import DocTypeRegistry


def _invoice_descriptor() -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name="hu_invoice",
        display_name="HU Invoice",
        type_classifier=TypeClassifierConfig(
            rules=[
                RuleSpec(kind="regex", weight=0.5, pattern=r"\bSzámla\b"),
                RuleSpec(kind="keyword_list", weight=0.5, keywords=["nettó"], threshold=1),
            ],
            llm_fallback=True,
            llm_threshold_below=0.7,
        ),
        extraction=ExtractionConfig(
            workflow="invoice_extraction_chain",
            fields=[FieldSpec(name="invoice_number", type="string", required=True)],
        ),
        intent_routing=IntentRoutingConfig(
            default="process",
            conditions=[
                IntentRoutingRule(
                    if_expr="extracted.total_gross > 1000000",
                    intent="route_to_human",
                    reason="Magas összegű",
                ),
                IntentRoutingRule(
                    if_expr="doc_type_confidence < 0.75",
                    intent="route_to_human",
                    reason="Bizonytalan",
                ),
            ],
        ),
    )


def _id_card_descriptor() -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name="hu_id_card",
        display_name="HU ID card",
        pii_level="high",
        type_classifier=TypeClassifierConfig(
            rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"MAGYARORSZÁG")],
            llm_fallback=False,  # PII descriptor — no LLM fallback by default
            llm_threshold_below=0.65,
        ),
        extraction=ExtractionConfig(
            workflow="id_card_extraction_chain",
            fields=[FieldSpec(name="id_number", type="string", required=True)],
        ),
        intent_routing=IntentRoutingConfig(
            default="route_to_human",
            pii_redaction=True,
        ),
    )


def _registry_with(*descriptors: DocTypeDescriptor) -> DocTypeRegistry:
    """Build a registry that loads from a temp empty dir + runtime registers descriptors."""
    import tempfile

    tmp = tempfile.mkdtemp()
    reg = DocTypeRegistry(bootstrap_dir=tmp)
    for d in descriptors:
        reg.register_doctype(d)
    return reg


# ---------------------------------------------------------------------------
# classify (stage 1+2)
# ---------------------------------------------------------------------------


class TestOrchestratorClassify:
    @pytest.mark.asyncio
    async def test_no_descriptors_returns_none(self):
        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        ctx = ClassifierInput(text="anything")
        match, descriptor = await orch.classify(ctx, tenant_id="t1")
        assert match is None
        assert descriptor is None

    @pytest.mark.asyncio
    async def test_rule_match_returns_descriptor(self):
        reg = _registry_with(_invoice_descriptor())
        orch = DocumentRecognizerOrchestrator(registry=reg)
        ctx = ClassifierInput(text="Számla — nettó 10000")
        match, descriptor = await orch.classify(ctx, tenant_id="t1")
        assert match is not None
        assert match.doc_type == "hu_invoice"
        assert descriptor is not None
        assert descriptor.name == "hu_invoice"

    @pytest.mark.asyncio
    async def test_doc_type_hint_short_circuits(self):
        reg = _registry_with(_invoice_descriptor())
        orch = DocumentRecognizerOrchestrator(registry=reg)
        # Text matches NOTHING but the hint forces hu_invoice resolution
        ctx = ClassifierInput(text="random gibberish")
        match, descriptor = await orch.classify(ctx, tenant_id="t1", doc_type_hint="hu_invoice")
        assert match is not None
        assert match.confidence == 1.0  # synthesized full-confidence
        assert descriptor is not None

    @pytest.mark.asyncio
    async def test_unknown_hint_falls_through_to_rule_engine(self):
        reg = _registry_with(_invoice_descriptor())
        orch = DocumentRecognizerOrchestrator(registry=reg)
        ctx = ClassifierInput(text="Számla — nettó 10000")
        # Hint refers to a non-existent doc-type — orchestrator ignores it
        # and runs the rule engine.
        match, descriptor = await orch.classify(
            ctx, tenant_id="t1", doc_type_hint="hu_passport_unknown"
        )
        assert match is not None
        assert match.doc_type == "hu_invoice"  # rule engine picked it up
        assert descriptor is not None


class TestOrchestratorLLMFallback:
    @pytest.mark.asyncio
    async def test_low_confidence_invokes_llm(self):
        invoice = _invoice_descriptor()
        # Drop weight so even on full match the score is < 0.7 threshold
        invoice = invoice.model_copy(
            update={
                "type_classifier": TypeClassifierConfig(
                    rules=[
                        RuleSpec(kind="regex", weight=0.3, pattern=r"\bSzámla\b"),
                        RuleSpec(kind="keyword_list", weight=0.3, keywords=["nettó"], threshold=1),
                    ],
                    llm_fallback=True,
                    llm_threshold_below=0.7,
                )
            }
        )
        reg = _registry_with(invoice)

        called: dict[str, int] = {"count": 0}

        async def fake_llm(descriptors, ctx):
            called["count"] += 1
            return ("hu_invoice", 0.95)

        orch = DocumentRecognizerOrchestrator(registry=reg, llm_classify_fn=fake_llm)
        ctx = ClassifierInput(text="Számla nettó")  # rule score 1.0 normalized to 1.0...
        # Actually with rules sum 0.6 and both fire, normalized = 0.6/0.6 = 1.0.
        # We need a partial match for fallback.

        # Partial match only — only the regex fires
        ctx = ClassifierInput(text="Számla without keyword2")
        # Rule-engine score = 0.3, normalized = 0.3/0.6 = 0.5 < threshold 0.7
        match, descriptor = await orch.classify(ctx, tenant_id="t1")
        assert match is not None
        # LLM fired and returned higher confidence
        assert called["count"] == 1
        assert match.confidence == 0.95
        assert descriptor is not None

    @pytest.mark.asyncio
    async def test_high_confidence_no_llm_call(self):
        reg = _registry_with(_invoice_descriptor())
        called: dict[str, int] = {"count": 0}

        async def fake_llm(descriptors, ctx):
            called["count"] += 1
            return None

        orch = DocumentRecognizerOrchestrator(registry=reg, llm_classify_fn=fake_llm)
        ctx = ClassifierInput(text="Számla — nettó 10000")  # Both rules fire, score=1.0
        match, descriptor = await orch.classify(ctx, tenant_id="t1")
        assert called["count"] == 0  # LLM not invoked when above threshold

    @pytest.mark.asyncio
    async def test_llm_returning_none_keeps_rule_match(self):
        invoice = _invoice_descriptor()
        invoice = invoice.model_copy(
            update={
                "type_classifier": TypeClassifierConfig(
                    rules=[RuleSpec(kind="regex", weight=0.3, pattern=r"\bSzámla\b")],
                    llm_fallback=True,
                    llm_threshold_below=0.7,
                )
            }
        )
        reg = _registry_with(invoice)

        async def fake_llm_none(descriptors, ctx):
            return None  # LLM gave up

        orch = DocumentRecognizerOrchestrator(registry=reg, llm_classify_fn=fake_llm_none)
        ctx = ClassifierInput(text="Számla")
        match, _ = await orch.classify(ctx, tenant_id="t1")
        # Rule match preserved despite LLM returning None
        assert match is not None
        assert match.doc_type == "hu_invoice"

    @pytest.mark.asyncio
    async def test_llm_exception_swallowed(self):
        invoice = _invoice_descriptor()
        invoice = invoice.model_copy(
            update={
                "type_classifier": TypeClassifierConfig(
                    rules=[RuleSpec(kind="regex", weight=0.3, pattern=r"\bSzámla\b")],
                    llm_fallback=True,
                    llm_threshold_below=0.7,
                )
            }
        )
        reg = _registry_with(invoice)

        async def fake_llm_raises(descriptors, ctx):
            raise RuntimeError("LLM API down")

        orch = DocumentRecognizerOrchestrator(registry=reg, llm_classify_fn=fake_llm_raises)
        ctx = ClassifierInput(text="Számla")
        match, _ = await orch.classify(ctx, tenant_id="t1")
        # Rule match preserved despite LLM raising
        assert match is not None
        assert match.doc_type == "hu_invoice"


# ---------------------------------------------------------------------------
# route_intent (stage 4)
# ---------------------------------------------------------------------------


class TestOrchestratorRouteIntent:
    def test_default_intent_when_no_rule_fires(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        descriptor = _invoice_descriptor()
        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.9)
        extraction = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={"total_gross": DocFieldValue(value=500000, confidence=0.95)},
        )
        decision = orch.route_intent(descriptor, extraction, match)
        assert decision.intent == "process"  # default
        assert decision.reason == "default"

    def test_high_amount_routes_to_human(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        descriptor = _invoice_descriptor()
        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.9)
        extraction = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={"total_gross": DocFieldValue(value=2000000, confidence=0.95)},
        )
        decision = orch.route_intent(descriptor, extraction, match)
        assert decision.intent == "route_to_human"
        assert "Magas összegű" in decision.reason

    def test_low_doc_type_confidence_routes_to_human(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        descriptor = _invoice_descriptor()
        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.65)  # < 0.75
        extraction = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={"total_gross": DocFieldValue(value=500000, confidence=0.95)},
        )
        decision = orch.route_intent(descriptor, extraction, match)
        assert decision.intent == "route_to_human"
        assert "Bizonytalan" in decision.reason

    def test_first_matching_rule_wins(self):
        from aiflow.contracts.doc_recognition import DocTypeMatch

        # Both rules will fire; first one (Magas összegű) should win
        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        descriptor = _invoice_descriptor()
        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.5)  # also < 0.75
        extraction = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={"total_gross": DocFieldValue(value=2000000, confidence=0.95)},
        )
        decision = orch.route_intent(descriptor, extraction, match)
        # First rule (Magas összegű) wins per declared order
        assert decision.intent == "route_to_human"
        assert "Magas összegű" in decision.reason

    def test_safe_eval_error_skips_rule(self):
        """If a rule's if_expr is malformed, the orchestrator skips it
        (logs warning) and continues to the next rule."""
        from aiflow.contracts.doc_recognition import DocTypeMatch

        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        descriptor = DocTypeDescriptor(
            name="x",
            display_name="x",
            type_classifier=TypeClassifierConfig(rules=[]),
            extraction=ExtractionConfig(workflow="x", fields=[FieldSpec(name="y", type="string")]),
            intent_routing=IntentRoutingConfig(
                default="process",
                conditions=[
                    IntentRoutingRule(
                        if_expr="this is not valid python ! @",
                        intent="reject",
                        reason="bad",
                    ),
                    IntentRoutingRule(
                        if_expr="doc_type_confidence < 0.5",
                        intent="route_to_human",
                        reason="ok",
                    ),
                ],
            ),
        )
        match = DocTypeMatch(doc_type="x", confidence=0.4)
        extraction = DocExtractionResult(doc_type="x", extracted_fields={})
        decision = orch.route_intent(descriptor, extraction, match)
        # First rule errored → skipped; second rule fired
        assert decision.intent == "route_to_human"


# ---------------------------------------------------------------------------
# run() end-to-end
# ---------------------------------------------------------------------------


class TestOrchestratorRun:
    @pytest.mark.asyncio
    async def test_no_match_returns_none(self):
        reg = _registry_with(_invoice_descriptor())
        orch = DocumentRecognizerOrchestrator(registry=reg)
        ctx = ClassifierInput(text="meeting agenda")
        result = await orch.run(ctx, tenant_id="t1")
        assert result is None

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        reg = _registry_with(_invoice_descriptor())
        orch = DocumentRecognizerOrchestrator(registry=reg)
        ctx = ClassifierInput(text="Számla — nettó 10000")
        result = await orch.run(ctx, tenant_id="t1")
        assert result is not None
        match, extraction, intent = result
        assert match.doc_type == "hu_invoice"
        # Extraction is empty in SV-2 — SV-3 wires the PromptWorkflow
        assert extraction.extracted_fields == {}
        # Default intent fires (no rule matches because extracted_fields is empty)
        # ... actually doc_type_confidence < 0.75 won't fire since we have full match
        assert intent.intent == "process"


# ---------------------------------------------------------------------------
# to_audit_payload (PII redaction)
# ---------------------------------------------------------------------------


class TestAuditPayload:
    def test_no_redaction(self):
        from aiflow.contracts.doc_recognition import DocIntentDecision, DocTypeMatch

        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.9)
        extraction = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={
                "invoice_number": DocFieldValue(value="INV-1", confidence=0.95),
            },
        )
        intent = DocIntentDecision(intent="process", reason="ok")
        payload = orch.to_audit_payload(
            match, extraction, intent, tenant_id="t1", pii_redaction=False
        )
        assert payload["extracted_fields"]["invoice_number"]["value"] == "INV-1"
        assert payload["pii_redacted"] is False

    def test_pii_redaction_replaces_values(self):
        from aiflow.contracts.doc_recognition import DocIntentDecision, DocTypeMatch

        reg = _registry_with()
        orch = DocumentRecognizerOrchestrator(registry=reg)
        match = DocTypeMatch(doc_type="hu_id_card", confidence=0.95)
        extraction = DocExtractionResult(
            doc_type="hu_id_card",
            extracted_fields={
                "id_number": DocFieldValue(value="123456AB", confidence=0.92),
                "full_name": DocFieldValue(value="Kiss Anna", confidence=0.95),
            },
        )
        intent = DocIntentDecision(intent="route_to_human", reason="PII")
        payload = orch.to_audit_payload(
            match, extraction, intent, tenant_id="t1", pii_redaction=True
        )
        # Values are redacted; field NAMES + confidences are preserved
        assert payload["extracted_fields"]["id_number"]["value"] == "<redacted>"
        assert payload["extracted_fields"]["id_number"]["confidence"] == 0.92
        assert payload["extracted_fields"]["full_name"]["value"] == "<redacted>"
        assert payload["pii_redacted"] is True
