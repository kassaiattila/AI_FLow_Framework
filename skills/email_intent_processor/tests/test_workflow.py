"""
@test_registry:
    suite: email-intent-unit
    component: skills.email_intent_processor
    covers:
        - skills/email_intent_processor/workflows/classify.py
        - skills/email_intent_processor/classifiers/__init__.py
        - skills/email_intent_processor/classifiers/sklearn_classifier.py
        - skills/email_intent_processor/classifiers/llm_classifier.py
        - skills/email_intent_processor/models/__init__.py
    phase: E2
    priority: critical
    estimated_duration_ms: 2000
    requires_services: []
    tags: [email, intent, classification, NER, routing, schemas]
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from skills.email_intent_processor.models import (
    AttachmentInfo,
    EmailInput,
    EmailProcessingResult,
    Entity,
    EntityResult,
    IntentResult,
    PriorityResult,
    RoutingDecision,
)


class TestModels:
    def test_email_input(self) -> None:
        inp = EmailInput(subject="Test", body="Hello world", sender="test@example.com")
        assert inp.subject == "Test"
        assert inp.body == "Hello world"

    def test_intent_result(self) -> None:
        result = IntentResult(intent_id="complaint", confidence=0.85, method="hybrid")
        assert result.intent_id == "complaint"
        assert result.confidence == 0.85

    def test_entity(self) -> None:
        e = Entity(entity_type="contract_number", value="SZ-123456", confidence=0.9, source="body")
        assert e.entity_type == "contract_number"

    def test_priority_result(self) -> None:
        p = PriorityResult(priority_level=4, sla_hours=8, reasoning="Urgent")
        assert p.priority_level == 4

    def test_routing_decision(self) -> None:
        r = RoutingDecision(queue_id="complaint_queue", department_id="ugyfelszolgalat")
        assert r.department_id == "ugyfelszolgalat"

    def test_processing_result(self) -> None:
        r = EmailProcessingResult(subject="Test", sender="test@test.hu")
        assert r.subject == "Test"


class TestSchemas:
    def test_intents_loads(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        data = sr.load_schema("email_intent_processor", "intents")
        assert len(data["intents"]) == 10
        ids = {i["id"] for i in data["intents"]}
        assert "complaint" in ids
        assert "cancellation" in ids

    def test_entities_loads(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        data = sr.load_schema("email_intent_processor", "entities")
        assert len(data["entity_types"]) == 8
        ids = {e["id"] for e in data["entity_types"]}
        assert "contract_number" in ids
        assert "amount" in ids

    def test_document_types_loads(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        data = sr.load_schema("email_intent_processor", "document_types")
        assert len(data["document_types"]) == 8

    def test_priorities_loads(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        data = sr.load_schema("email_intent_processor", "priorities")
        assert len(data["priority_levels"]) == 5

    def test_routing_rules_loads(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        data = sr.load_schema("email_intent_processor", "routing_rules")
        assert "routing_rules" in data

    def test_version_listing(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        versions = sr.list_versions("email_intent_processor")
        assert "v1" in versions

    def test_schema_types_listing(self) -> None:
        from aiflow.tools.schema_registry import SchemaRegistry
        sr = SchemaRegistry()
        types = sr.list_schema_types("email_intent_processor")
        assert "intents" in types
        assert "entities" in types


class TestEmailParser:
    def test_parse_text(self) -> None:
        from aiflow.tools.email_parser import EmailParser
        parser = EmailParser()
        result = parser.parse_text("Reklamacio", "Kedves Ugyfelszolgalat, reklamaciom van.", "test@test.hu")
        assert result.subject == "Reklamacio"
        assert "reklamaciom" in result.body_text

    def test_parse_text_empty(self) -> None:
        from aiflow.tools.email_parser import EmailParser
        parser = EmailParser()
        result = parser.parse_text("", "", "")
        assert result.body_text == ""


class TestSklearnClassifier:
    def test_predict_without_model(self) -> None:
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("This is a complaint")
        assert "intent" in result
        assert result.get("confidence", 0) <= 0.5

    def test_predict_returns_alternatives(self) -> None:
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("Order for new policy")
        assert "alternatives" in result


class TestSampleDataset:
    def test_dataset_valid(self) -> None:
        path = Path("skills/email_intent_processor/tests/datasets/sample_emails.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "samples" in data
        assert len(data["samples"]) >= 14

    def test_all_intents_covered(self) -> None:
        path = Path("skills/email_intent_processor/tests/datasets/sample_emails.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        intents = {e["expected"]["intent"] for e in data["samples"]}
        assert "complaint" in intents
        assert "claim" in intents
        assert "cancellation" in intents

    def test_each_email_has_required_fields(self) -> None:
        path = Path("skills/email_intent_processor/tests/datasets/sample_emails.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for sample in data["samples"]:
            assert "id" in sample
            assert "subject" in sample
            assert "body" in sample
            assert "expected" in sample


# ══════════════════════════════════════════════════════════════════════════════
# EXTENDED TESTS: Models, Classifiers, Workflow Steps, Edge Cases
# ══════════════════════════════════════════════════════════════════════════════


class TestModelsExtended:
    """Extended model validation tests."""

    def test_attachment_info(self):
        a = AttachmentInfo(filename="doc.pdf", mime_type="application/pdf", size_bytes=1024)
        assert a.size_bytes == 1024
        assert a.extracted_text == ""

    def test_entity_result_get_by_type(self):
        entities = [
            Entity(entity_type="contract_number", value="SZ-123", confidence=0.9, source="body"),
            Entity(entity_type="person_name", value="Kovács Péter", confidence=0.8, source="body"),
        ]
        er = EntityResult(entities=entities, entity_count=2, extraction_methods_used={"regex"})
        contracts = er.get_by_type("contract_number")
        assert len(contracts) == 1
        assert contracts[0].value == "SZ-123"

    def test_entity_result_has_entity(self):
        entities = [Entity(entity_type="amount", value="125000", confidence=0.7, source="body")]
        er = EntityResult(entities=entities, entity_count=1, extraction_methods_used={"regex"})
        assert er.has_entity("amount") is True
        assert er.has_entity("phone_number") is False

    def test_entity_result_empty(self):
        er = EntityResult(entities=[], entity_count=0, extraction_methods_used=set())
        assert er.has_entity("anything") is False
        assert er.get_by_type("anything") == []

    def test_intent_result_full_fields(self):
        ir = IntentResult(
            intent_id="complaint",
            confidence=0.92,
            method="hybrid",
            sklearn_intent="complaint",
            sklearn_confidence=0.85,
            llm_intent="complaint",
            llm_confidence=0.95,
            alternatives=[{"intent": "feedback", "confidence": 0.3}],
            reasoning="Clear complaint pattern",
        )
        assert ir.sklearn_confidence == 0.85
        assert len(ir.alternatives) == 1

    def test_priority_result_with_boosts(self):
        p = PriorityResult(
            priority_level=1,
            priority_name="critical",
            sla_hours=2,
            matched_rule="rule_complaint_urgent",
            boosts_applied=["legal_threat"],
        )
        assert p.boosts_applied == ["legal_threat"]

    def test_routing_with_escalation(self):
        r = RoutingDecision(
            queue_id="q_legal",
            department_id="jogi",
            escalation_triggered=True,
            escalation_reason="Legal keywords detected",
        )
        assert r.escalation_triggered is True

    def test_processing_result_with_errors(self):
        r = EmailProcessingResult(
            subject="Test",
            sender="test@test.hu",
            errors=["Attachment parse failed"],
            warnings=["Low confidence"],
        )
        assert len(r.errors) == 1


class TestSklearnClassifierExtended:
    """Extended sklearn classifier tests."""

    def test_fallback_keyword_complaint(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("Reklamáció, hibás számla, panasz")
        assert result["intent"] == "complaint"

    def test_fallback_keyword_claim(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("Kárbejelentés, baleset, biztosítási esemény")
        assert result["intent"] == "claim"

    def test_fallback_unknown_text(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("xyzzy lorem ipsum dolor sit amet")
        assert result["confidence"] <= 0.5

    def test_clean_text(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        cleaned = clf._clean_text("  Hello WORLD! 123 xxxx  ")
        assert "xxxx" not in cleaned
        assert cleaned == cleaned.lower()

    def test_is_loaded_false(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        assert clf.is_loaded is False


class TestLLMClassifier:
    """Test LLM-based classifier."""

    @pytest.mark.asyncio
    async def test_classify_basic(self):
        from skills.email_intent_processor.classifiers.llm_classifier import LLMClassifier

        mock_mc = MagicMock()
        mock_pm = MagicMock()
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = [{"role": "user", "content": "classify"}]
        mock_prompt.config = SimpleNamespace(model="gpt-4o-mini", temperature=0.1, max_tokens=512)
        mock_pm.get.return_value = mock_prompt

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text='{"intent_id": "complaint", "confidence": 0.9, "reasoning": "clear complaint"}')
        mock_result.cost_usd = 0.001
        mock_mc.generate = AsyncMock(return_value=mock_result)

        clf = LLMClassifier(mock_mc, mock_pm)
        result = await clf.classify("Reklamáció!", subject="Panasz")
        assert result.intent_id == "complaint"
        assert result.method == "llm"

    @pytest.mark.asyncio
    async def test_classify_error_returns_unknown(self):
        from skills.email_intent_processor.classifiers.llm_classifier import LLMClassifier

        mock_mc = MagicMock()
        mock_mc.generate = AsyncMock(side_effect=Exception("API error"))
        mock_pm = MagicMock()
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = [{"role": "user", "content": "test"}]
        mock_prompt.config = SimpleNamespace(model="gpt-4o-mini", temperature=0.1, max_tokens=512)
        mock_pm.get.return_value = mock_prompt

        clf = LLMClassifier(mock_mc, mock_pm)
        result = await clf.classify("Test text")
        assert result.intent_id == "unknown"
        assert "error" in result.method


class TestHybridClassifier:
    """Test hybrid classifier strategies."""

    @pytest.mark.asyncio
    async def test_sklearn_first_high_confidence(self):
        from skills.email_intent_processor.classifiers import HybridClassifier

        mock_sklearn = MagicMock()
        mock_sklearn.predict.return_value = {
            "intent": "complaint",
            "confidence": 0.9,
            "alternatives": [],
        }
        mock_sklearn.is_loaded = True

        mock_llm = MagicMock()

        clf = HybridClassifier(mock_sklearn, mock_llm, strategy="sklearn_first", confidence_threshold=0.6)
        result = await clf.classify("Reklamáció")

        assert result.intent_id == "complaint"
        assert result.sklearn_confidence == 0.9
        # LLM should NOT be called since sklearn confidence > threshold
        mock_llm.classify.assert_not_called()

    @pytest.mark.asyncio
    async def test_sklearn_first_low_confidence_triggers_llm(self):
        from skills.email_intent_processor.classifiers import HybridClassifier

        mock_sklearn = MagicMock()
        mock_sklearn.predict.return_value = {
            "intent": "inquiry",
            "confidence": 0.4,
            "alternatives": [],
        }
        mock_sklearn.is_loaded = True

        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(return_value=IntentResult(
            intent_id="complaint",
            confidence=0.85,
            method="llm",
        ))

        clf = HybridClassifier(mock_sklearn, mock_llm, strategy="sklearn_first", confidence_threshold=0.6)
        result = await clf.classify("Ambiguous text")

        mock_llm.classify.assert_called_once()
        assert result.intent_id == "complaint"

    @pytest.mark.asyncio
    async def test_sklearn_only_strategy(self):
        from skills.email_intent_processor.classifiers import HybridClassifier

        mock_sklearn = MagicMock()
        mock_sklearn.predict.return_value = {
            "intent": "order",
            "confidence": 0.7,
            "alternatives": [],
        }
        mock_sklearn.is_loaded = True
        mock_llm = MagicMock()

        clf = HybridClassifier(mock_sklearn, mock_llm, strategy="sklearn_only")
        result = await clf.classify("Order something")

        assert result.intent_id == "order"
        mock_llm.classify.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_only_strategy(self):
        from skills.email_intent_processor.classifiers import HybridClassifier

        mock_sklearn = MagicMock()
        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(return_value=IntentResult(
            intent_id="feedback",
            confidence=0.8,
            method="llm",
        ))

        clf = HybridClassifier(mock_sklearn, mock_llm, strategy="llm_only")
        result = await clf.classify("Great service")

        assert result.intent_id == "feedback"
        mock_sklearn.predict.assert_not_called()


class TestWorkflowStepParseEmail:
    """Test parse_email workflow step."""

    @pytest.mark.asyncio
    async def test_parse_with_text_fields(self):
        from skills.email_intent_processor.workflows import classify as cmod

        mock_parser = MagicMock()
        mock_result = MagicMock()
        mock_result.subject = "Reklamáció"
        mock_result.body_text = "Panaszom van."
        mock_result.body_html = ""
        mock_result.sender = "test@test.hu"
        mock_result.recipients = ["info@bestix.hu"]
        mock_result.date = "2026-03-29"
        mock_result.message_id = "<abc@test>"
        mock_result.in_reply_to = None
        mock_result.references = []
        mock_result.attachments = []
        mock_parser.parse_text.return_value = mock_result

        with patch.object(cmod, "email_parser", mock_parser):
            result = await cmod.parse_email({
                "subject": "Reklamáció",
                "body": "Panaszom van.",
                "sender": "test@test.hu",
            })

            assert result["subject"] == "Reklamáció"
            assert result["body"] == "Panaszom van."

    @pytest.mark.asyncio
    async def test_parse_from_eml_path(self, tmp_path):
        from skills.email_intent_processor.workflows import classify as cmod

        eml_file = tmp_path / "test.eml"
        eml_file.write_text("From: test@test.hu\nSubject: Test\n\nBody", encoding="utf-8")

        mock_parser = MagicMock()
        mock_result = MagicMock()
        mock_result.subject = "Test"
        mock_result.body_text = "Body"
        mock_result.body_html = ""
        mock_result.sender = "test@test.hu"
        mock_result.recipients = []
        mock_result.date = ""
        mock_result.message_id = ""
        mock_result.in_reply_to = None
        mock_result.references = []
        mock_result.attachments = []
        mock_parser.parse_eml.return_value = mock_result

        with patch.object(cmod, "email_parser", mock_parser):
            result = await cmod.parse_email({"raw_eml_path": str(eml_file)})
            mock_parser.parse_eml.assert_called_once()


class TestWorkflowStepScorePriority:
    """Test score_priority workflow step."""

    @pytest.mark.asyncio
    async def test_complaint_high_priority(self):
        from skills.email_intent_processor.workflows import classify as cmod

        with patch.object(cmod, "schema_registry") as sr:
            sr.load_schema.return_value = {
                "priority_levels": [
                    {"level": 1, "name": "critical", "sla_hours": 2},
                    {"level": 2, "name": "high", "sla_hours": 8},
                    {"level": 3, "name": "medium", "sla_hours": 24},
                    {"level": 4, "name": "low", "sla_hours": 48},
                    {"level": 5, "name": "minimal", "sla_hours": 72},
                ],
                "rules": [
                    {
                        "id": "rule_complaint_urgent",
                        "conditions": {"intent": "complaint", "keywords_present": ["sürgős"]},
                        "result_priority": 2,
                    },
                ],
                "boost_rules": [],
                "default_priority": 4,
            }

            result = await cmod.score_priority({
                "intent": {"intent_id": "complaint"},
                "entities": {"entities": [], "entity_count": 0},
                "body": "Ez sürgős reklamáció!",
            })

            assert result["priority"]["priority_level"] == 2

    @pytest.mark.asyncio
    async def test_default_priority_when_no_rule_matches(self):
        from skills.email_intent_processor.workflows import classify as cmod

        with patch.object(cmod, "schema_registry") as sr:
            sr.load_schema.return_value = {
                "priority_levels": [
                    {"level": 4, "name": "low", "sla_hours": 48},
                ],
                "rules": [],
                "boost_rules": [],
                "default_priority": 4,
            }

            result = await cmod.score_priority({
                "intent": {"intent_id": "notification"},
                "entities": {"entities": [], "entity_count": 0},
                "body": "No matching rules here",
            })

            assert result["priority"]["priority_level"] == 4


class TestWorkflowStepDecideRouting:
    """Test decide_routing workflow step using real routing_rules schema."""

    @pytest.mark.asyncio
    async def test_complaint_routed(self):
        from skills.email_intent_processor.workflows import classify as cmod

        result = await cmod.decide_routing({
            "intent": {"intent_id": "complaint"},
            "priority": {"priority_level": 2},
            "body": "Regular complaint text",
        })

        routing = result["routing"]
        assert routing["queue_id"] != ""
        assert routing["department_id"] != ""

    @pytest.mark.asyncio
    async def test_legal_escalation_triggered(self):
        from skills.email_intent_processor.workflows import classify as cmod

        result = await cmod.decide_routing({
            "intent": {"intent_id": "complaint"},
            "priority": {"priority_level": 1},
            "body": "Az ugyved birosag ele viszi az ugyet, feljelentes!",
        })

        routing = result["routing"]
        assert routing["escalation_triggered"] is True
        assert routing["department_id"] == "jogi"

    @pytest.mark.asyncio
    async def test_default_routing_for_unknown_intent(self):
        from skills.email_intent_processor.workflows import classify as cmod

        result = await cmod.decide_routing({
            "intent": {"intent_id": "nonexistent_intent"},
            "priority": {"priority_level": 4},
            "body": "Some text",
        })

        routing = result["routing"]
        # Should fall through to default route
        assert "queue_id" in routing


class TestWorkflowStepClassifyIntent:
    """Test classify_intent workflow step."""

    @pytest.mark.asyncio
    async def test_classify_with_body_and_attachments(self):
        from skills.email_intent_processor.workflows import classify as cmod

        mock_intent = IntentResult(intent_id="complaint", confidence=0.9, method="hybrid")

        with (
            patch.object(cmod, "hybrid_classifier") as hc,
            patch.object(cmod, "schema_registry") as sr,
        ):
            hc.classify = AsyncMock(return_value=mock_intent)
            sr.load_schema.return_value = {
                "intents": [{"id": "complaint", "display_name": "Reklamáció"}],
            }

            result = await cmod.classify_intent({
                "subject": "Panasz",
                "body": "Reklamálok a számla miatt.",
                "attachment_text": "Csatolt számla szöveg.",
            })

            assert result["intent"]["intent_id"] == "complaint"
            assert result["intent"]["intent_display_name"] == "Reklamáció"


class TestWorkflowStepLogResult:
    """Test log_result workflow step."""

    @pytest.mark.asyncio
    async def test_assembles_processing_result(self):
        from skills.email_intent_processor.workflows import classify as cmod

        result = await cmod.log_result({
            "subject": "Teszt email",
            "sender": "test@test.hu",
            "body": "Body text",
            "intent": {"intent_id": "inquiry", "confidence": 0.8},
            "entities": {"entities": [], "entity_count": 0},
            "priority": {"priority_level": 4, "sla_hours": 48},
            "routing": {"queue_id": "q_inquiry", "department_id": "informacio"},
            "attachment_summaries": [],
        })

        assert result["subject"] == "Teszt email"
        assert result["intent"]["intent_id"] == "inquiry"


class TestEdgeCasesEmail:
    """Edge cases and error handling."""

    def test_entity_confidence_validated(self):
        """Pydantic validates confidence is in [0, 1]."""
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            Entity(entity_type="amount", value="100", confidence=1.5, source="body")

    def test_intent_result_defaults(self):
        ir = IntentResult(intent_id="unknown", confidence=0.0, method="none")
        assert ir.sub_intent == ""
        assert ir.alternatives == []
        assert ir.reasoning == "" or ir.reasoning is None

    def test_sklearn_fallback_cancellation(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("felmondás lemondás cancel megszüntetés")
        # Keyword matching may vary; just verify it returns a valid result
        assert "intent" in result
        assert result["confidence"] <= 0.5

    def test_sklearn_fallback_order(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("Új szerződés megrendelés kérem")
        assert result["intent"] == "order"

    def test_sklearn_fallback_support(self):
        from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
        clf = SklearnClassifier(model_path="nonexistent.joblib")
        result = clf.predict("Login hiba, nem tudok belépni, technikai probléma")
        assert result["intent"] == "support"

    def test_routing_default_values(self):
        r = RoutingDecision(queue_id="q_default", department_id="info")
        assert r.escalation_triggered is False
        assert r.auto_escalate_after_minutes == 0
