"""Pipeline v1.3 → v1.4 auto-upgrade E2E.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, compat, pipeline]

Validates 106_ Section 7 Day 16-17 and src/aiflow/pipeline/compatibility.py:
- detect_pipeline_version() recognises v1.3 + v1.4 markers
- upgrade_pipeline_v1_3_to_v1_4() converts email_adapter → intake_normalize
- upgrade rewrites document_adapter.extract → extract_from_package
- Converted pipelines are detected as v1.4 on the next pass (idempotent-ish)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aiflow.pipeline.compatibility import (
    detect_pipeline_version,
    upgrade_pipeline_v1_3_to_v1_4,
)


@pytest.fixture
def legacy_pipeline(legacy_pipeline_path: Path) -> dict:
    with open(legacy_pipeline_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestDetectPipelineVersion:
    def test_detects_v1_3_from_fixture(self, legacy_pipeline: dict) -> None:
        assert detect_pipeline_version(legacy_pipeline) == "v1.3"

    def test_detects_v1_4_via_explicit_version_field(self) -> None:
        yaml_dict = {"version": "2.0", "steps": []}
        assert detect_pipeline_version(yaml_dict) == "v1.4"

    def test_detects_v1_4_via_intake_normalize_adapter(self) -> None:
        yaml_dict = {
            "version": "1.3",
            "steps": [{"name": "intake", "adapter": "intake_normalize"}],
        }
        assert detect_pipeline_version(yaml_dict) == "v1.4"

    def test_missing_version_and_adapters_defaults_to_v1_3(self) -> None:
        assert detect_pipeline_version({"steps": []}) == "v1.3"
        assert detect_pipeline_version({}) == "v1.3"


class TestUpgradeFromFixture:
    def test_version_bumped_to_2_0(self, legacy_pipeline: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        assert upgraded["version"] == "2.0"

    def test_email_adapter_replaced_with_intake_normalize(self, legacy_pipeline: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        adapters = [s.get("adapter") for s in upgraded["steps"]]
        assert "email_adapter" not in adapters
        assert "intake_normalize" in adapters

    def test_intake_normalize_preserves_source_config(self, legacy_pipeline: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        intake_step = next(s for s in upgraded["steps"] if s.get("adapter") == "intake_normalize")
        assert intake_step["config"]["source_type"] == "email"
        assert intake_step["config"]["source_config"]["mailbox"] == "ops@example.com"

    def test_document_adapter_extract_rewritten(self, legacy_pipeline: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        doc_step = next(s for s in upgraded["steps"] if s.get("adapter") == "document_adapter")
        assert doc_step["method"] == "extract_from_package"
        assert doc_step["for_each"] == "{{ intake.output.package }}"

    def test_passthrough_steps_unchanged(self, legacy_pipeline: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        store = next(s for s in upgraded["steps"] if s.get("adapter") == "postgres_adapter")
        assert store["config"]["table"] == "extraction_results"

    def test_step_count_preserved(self, legacy_pipeline: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        assert len(upgraded["steps"]) == len(legacy_pipeline["steps"])


class TestDetectAfterUpgrade:
    def test_upgraded_pipeline_detected_as_v1_4(self, legacy_pipeline: dict) -> None:
        assert detect_pipeline_version(legacy_pipeline) == "v1.3"
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        assert detect_pipeline_version(upgraded) == "v1.4"

    def test_upgrade_does_not_mutate_input(self, legacy_pipeline: dict) -> None:
        original_version = legacy_pipeline.get("version")
        original_steps = list(legacy_pipeline["steps"])
        upgrade_pipeline_v1_3_to_v1_4(legacy_pipeline)
        assert legacy_pipeline.get("version") == original_version
        assert legacy_pipeline["steps"] == original_steps


class TestPipelineWithoutEmailAdapter:
    def test_pipeline_with_only_document_adapter_still_bumps_version(self) -> None:
        yaml_dict = {
            "version": "1.3",
            "steps": [
                {
                    "name": "doc",
                    "adapter": "document_adapter",
                    "method": "extract",
                    "for_each": "{{ input.files }}",
                }
            ],
        }
        upgraded = upgrade_pipeline_v1_3_to_v1_4(yaml_dict)
        assert upgraded["version"] == "2.0"
        assert upgraded["steps"][0]["method"] == "extract_from_package"
        assert upgraded["steps"][0]["for_each"] == "{{ intake.output.package }}"

    def test_pipeline_with_no_matchable_steps_just_bumps_version(self) -> None:
        yaml_dict = {
            "version": "1.3",
            "steps": [{"name": "a", "adapter": "custom_adapter", "config": {"k": 1}}],
        }
        upgraded = upgrade_pipeline_v1_3_to_v1_4(yaml_dict)
        assert upgraded["version"] == "2.0"
        assert len(upgraded["steps"]) == 1
        assert upgraded["steps"][0]["adapter"] == "custom_adapter"
