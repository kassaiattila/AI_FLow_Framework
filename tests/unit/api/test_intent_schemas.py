"""
@test_registry:
    suite: api-unit
    component: api.intent_schemas
    covers: [src/aiflow/api/v1/intent_schemas.py]
    phase: S11
    priority: high
    estimated_duration_ms: 300
    requires_services: []
    tags: [intent, schema, crud, api]
"""

from __future__ import annotations

from aiflow.api.v1.intent_schemas import (
    IntentDefinition,
    IntentRouting,
    IntentSchemaCreateRequest,
    IntentSchemaItem,
    IntentSchemaListResponse,
    IntentSchemaUpdateRequest,
    IntentTestRequest,
    IntentTestResult,
)


class TestIntentSchemaModels:
    """Test Pydantic models for intent schemas."""

    def test_intent_routing_defaults(self):
        """IntentRouting has sensible defaults."""
        r = IntentRouting()
        assert r.queue == ""
        assert r.priority_boost == 0
        assert r.sla_hours == 48

    def test_intent_definition_full(self):
        """IntentDefinition with all fields."""
        intent = IntentDefinition(
            id="complaint",
            display_name="Panasz",
            description="Customer complaint",
            keywords_hu=["panasz", "reklamacio"],
            keywords_en=["complaint"],
            examples=["Reklamaciom van"],
            routing=IntentRouting(queue="support", priority_boost=1, sla_hours=24),
            ml_label="complaint",
            sub_intents=["billing_complaint"],
            auto_action=None,
        )
        assert intent.id == "complaint"
        assert len(intent.keywords_hu) == 2
        assert intent.routing.sla_hours == 24

    def test_intent_definition_minimal(self):
        """IntentDefinition with only required field."""
        intent = IntentDefinition(id="test")
        assert intent.display_name == ""
        assert intent.keywords_hu == []
        assert intent.auto_action is None

    def test_schema_item_serialization(self):
        """IntentSchemaItem serializes correctly."""
        item = IntentSchemaItem(
            id="abc-123",
            name="email-intents",
            version="1.1",
            description="Email classification intents",
            intents=[
                IntentDefinition(id="complaint", display_name="Complaint"),
                IntentDefinition(id="inquiry", display_name="Inquiry"),
            ],
            customer="bestix",
        )
        d = item.model_dump()
        assert d["name"] == "email-intents"
        assert len(d["intents"]) == 2
        assert d["customer"] == "bestix"

    def test_create_request_defaults(self):
        """Create request has default customer and version."""
        req = IntentSchemaCreateRequest(name="test-schema")
        assert req.version == "1.0"
        assert req.customer == "default"
        assert req.intents == []

    def test_update_request_partial(self):
        """Update request allows partial updates."""
        req = IntentSchemaUpdateRequest(name="new-name")
        assert req.name == "new-name"
        assert req.version is None
        assert req.intents is None

    def test_list_response_source(self):
        """List response has source=backend."""
        resp = IntentSchemaListResponse(schemas=[], total=0)
        assert resp.source == "backend"

    def test_test_request(self):
        """Test request model works."""
        req = IntentTestRequest(text="Reklamaciom van a szamlavel")
        assert req.language == "hu"

    def test_test_result(self):
        """Test result model works."""
        result = IntentTestResult(
            intent_id="complaint",
            intent_name="Panasz",
            confidence=0.8,
            matched_keywords=["reklamacio"],
        )
        assert result.confidence == 0.8
        assert "reklamacio" in result.matched_keywords
