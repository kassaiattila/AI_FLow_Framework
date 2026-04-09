"""
@test_registry:
    suite: pipeline-unit
    component: skills.invoice_finder.prompts
    covers: [skills/invoice_finder/prompts/invoice_field_extractor.yaml]
    phase: B3
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, prompt, invoice-finder, extraction]
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jinja2 import Template

PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "invoice_finder"
    / "prompts"
    / "invoice_field_extractor.yaml"
)


@pytest.fixture(scope="module")
def prompt_data() -> dict:
    return yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))


class TestInvoiceFieldExtractorPrompt:
    """Validate invoice_field_extractor.yaml prompt structure and content."""

    def test_field_extractor_prompt_yaml_valid(self, prompt_data: dict) -> None:
        """YAML parses correctly and has all required top-level keys."""
        assert PROMPT_PATH.exists(), f"Prompt not found at {PROMPT_PATH}"
        assert isinstance(prompt_data, dict)
        assert prompt_data["name"] == "invoice_finder/field_extractor"
        assert "version" in prompt_data
        assert "system" in prompt_data
        assert "user" in prompt_data
        assert "config" in prompt_data
        assert "metadata" in prompt_data
        # Config must have model and temperature
        config = prompt_data["config"]
        assert "model" in config
        assert config["temperature"] == 0.0
        assert config.get("response_format") == "json_object"

    def test_field_extractor_prompt_has_hu_fields(self, prompt_data: dict) -> None:
        """System prompt contains Hungarian-specific field references."""
        system = prompt_data["system"]
        # Hungarian tax number format
        assert "XXXXXXXX-X-XX" in system
        assert "12345678-2-41" in system
        # Hungarian VAT rates (AFA)
        assert "27%" in system
        assert "18%" in system
        assert "5%" in system
        # Hungarian keywords
        assert "AFA" in system or "ÁFA" in system
        assert "HUF" in system
        # Key output fields
        assert "invoice_number" in system
        assert "vendor" in system
        assert "buyer" in system
        assert "line_items" in system
        assert "totals" in system

    def test_field_extractor_jinja2_renders(self, prompt_data: dict) -> None:
        """User template renders correctly with {{ raw_text }} variable."""
        user_template = Template(prompt_data["user"])
        sample_text = "Szamla szam: INV-2026-001\nKiallito: Test Kft.\nOsszeg: 127.000 Ft"
        rendered = user_template.render(raw_text=sample_text)
        assert "INV-2026-001" in rendered
        assert "Test Kft." in rendered
        assert "127.000 Ft" in rendered
