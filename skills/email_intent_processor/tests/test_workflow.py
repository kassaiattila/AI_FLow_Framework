"""
@test_registry:
    suite: email-intent-unit
    component: skills.email_intent_processor
    covers: [skills/email_intent_processor/workflows/classify.py]
    phase: E2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [email, intent, classification, NER, routing, schemas]
"""
from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from skills.email_intent_processor.models import (
    EmailInput, IntentResult, Entity, PriorityResult, RoutingDecision,
    EmailProcessingResult,
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
        assert len(data["intents"]) == 7
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
