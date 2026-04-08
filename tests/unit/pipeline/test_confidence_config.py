"""
@test_registry:
    suite: unit
    component: skills.invoice_finder.confidence_config
    covers: [skills/invoice_finder/confidence_config.yaml]
    phase: B3.5
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [confidence, config, yaml, invoice-finder]
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aiflow.engine.confidence_router import ConfidenceRoutingConfig

CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "skills" / "invoice_finder" / "confidence_config.yaml"
)


@pytest.fixture(scope="module")
def config() -> dict:
    assert CONFIG_PATH.exists(), f"Config file not found: {CONFIG_PATH}"
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


class TestConfidenceConfigYAML:
    def test_yaml_has_required_top_level_keys(self, config: dict) -> None:
        """Config must expose routing, field_weights, source_quality_scores, mandatory_fields."""
        assert "routing" in config
        assert "field_weights" in config
        assert "source_quality_scores" in config
        assert "mandatory_fields" in config
        assert "field_types" in config

    def test_routing_thresholds_ordered_and_valid(self, config: dict) -> None:
        """reject <= review <= auto_approve, all in [0, 1]."""
        routing = config["routing"]
        auto = routing["auto_approve_threshold"]
        review = routing["review_threshold"]
        reject = routing["reject_threshold"]

        assert 0.0 <= reject <= review <= auto <= 1.0, (
            f"Thresholds out of order: reject={reject}, review={review}, auto={auto}"
        )
        # Must pass the ConfidenceRoutingConfig Pydantic validator
        ConfidenceRoutingConfig(
            auto_approve_threshold=auto,
            review_threshold=review,
            reject_threshold=reject,
            low_confidence_field_threshold=routing.get("low_confidence_field_threshold", 0.70),
        )

    def test_mandatory_fields_are_subset_of_field_types(self, config: dict) -> None:
        """Every mandatory field must have a declared type + weight."""
        mandatory = set(config["mandatory_fields"])
        field_types = set(config["field_types"].keys())
        field_weights = set(config["field_weights"].keys())

        missing_types = mandatory - field_types
        assert not missing_types, f"Mandatory fields without declared type: {missing_types}"

        missing_weights = mandatory - field_weights
        assert not missing_weights, (
            f"Mandatory fields without aggregation weight: {missing_weights}"
        )

    def test_source_quality_scores_in_valid_range(self, config: dict) -> None:
        """All parser quality multipliers in [0, 1]."""
        for parser, score in config["source_quality_scores"].items():
            assert 0.0 <= score <= 1.0, f"source_quality_scores[{parser}] = {score} out of [0, 1]"
