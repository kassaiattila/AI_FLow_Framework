"""
@test_registry:
    suite: api-unit
    component: api.v1.emails (FU-2 intent_class resolver)
    covers:
        - src/aiflow/api/v1/emails.py
        - skills/email_intent_processor/schemas/v1/intents.json
    phase: sprint-o-fu-2
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [api, emails, intent_class, sprint-o, fu-2]

Sprint O FU-2 — validates that every intent in the v1 schema carries an
``intent_class`` pointing at one of the five abstract categories, and that
the module-level resolver returns the right class for a known ``intent_id``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiflow.api.v1 import emails as emails_module

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "skills" / "email_intent_processor" / "schemas" / "v1" / "intents.json"
VALID_CLASSES = {"EXTRACT", "INFORMATION_REQUEST", "SUPPORT", "SPAM", "OTHER"}


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    """Clear the module-level memo so each test starts clean."""
    emails_module._INTENT_CLASS_MAP = None


class TestIntentSchemaIntegrity:
    """FU-2 hard contract: every intent declares a valid intent_class."""

    def test_schema_declares_intent_classes_section(self) -> None:
        data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert "intent_classes" in data
        assert set(data["intent_classes"]["values"]) == VALID_CLASSES

    def test_every_intent_has_intent_class(self) -> None:
        data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        intents = data["intents"]
        assert len(intents) == 12, "Sprint K v1 schema pins 12 intents"
        for intent in intents:
            assert "intent_class" in intent, f"intent '{intent.get('id')}' missing intent_class"
            assert intent["intent_class"] in VALID_CLASSES

    def test_schema_version_bumped(self) -> None:
        data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.3"


class TestResolveIntentClass:
    """Module-level resolver surface (used by GET /api/v1/emails/{id})."""

    def test_known_intents_map_to_expected_classes(self) -> None:
        # Sanity spot-checks covering all five classes.
        assert emails_module._resolve_intent_class("invoice_received") == "EXTRACT"
        assert emails_module._resolve_intent_class("order") == "EXTRACT"
        assert emails_module._resolve_intent_class("inquiry") == "INFORMATION_REQUEST"
        assert emails_module._resolve_intent_class("support") == "SUPPORT"
        assert emails_module._resolve_intent_class("marketing") == "SPAM"
        assert emails_module._resolve_intent_class("notification") == "SPAM"
        assert emails_module._resolve_intent_class("complaint") == "OTHER"

    def test_unknown_intent_returns_none(self) -> None:
        assert emails_module._resolve_intent_class("does_not_exist") is None

    def test_none_or_empty_intent_id_returns_none(self) -> None:
        assert emails_module._resolve_intent_class(None) is None
        assert emails_module._resolve_intent_class("") is None

    def test_map_is_cached(self) -> None:
        assert emails_module._INTENT_CLASS_MAP is None
        emails_module._resolve_intent_class("invoice_received")
        first = emails_module._INTENT_CLASS_MAP
        assert first is not None
        emails_module._resolve_intent_class("order")
        # same dict instance — no re-load on subsequent calls
        assert emails_module._INTENT_CLASS_MAP is first
