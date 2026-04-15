"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.compatibility
    covers: [src/aiflow/pipeline/compatibility.py]
    phase: D0.7
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, compatibility, version-detection, auto-upgrade]
"""

from __future__ import annotations

from aiflow.pipeline.compatibility import (
    detect_pipeline_version,
    upgrade_pipeline_v1_3_to_v1_4,
)

# --- Fixtures: sample pipelines ---


def _v13_email_pipeline() -> dict:
    return {
        "name": "invoice_email_pipeline",
        "steps": [
            {"name": "fetch_email", "adapter": "email_adapter", "config": {"folder": "INBOX"}},
            {
                "name": "extract_doc",
                "adapter": "document_adapter",
                "method": "extract",
                "for_each": "{{ emails }}",
            },
            {"name": "notify", "adapter": "notification_adapter", "method": "send"},
        ],
    }


def _v14_pipeline() -> dict:
    return {
        "name": "invoice_v2_pipeline",
        "version": "2.0",
        "steps": [
            {"name": "intake", "adapter": "intake_normalize", "config": {"source_type": "email"}},
            {
                "name": "extract_doc",
                "adapter": "document_adapter",
                "method": "extract_from_package",
            },
        ],
    }


def _v13_no_email_pipeline() -> dict:
    return {
        "name": "simple_pipeline",
        "steps": [
            {"name": "parse", "adapter": "parser_adapter", "method": "parse"},
            {"name": "classify", "adapter": "classifier_adapter", "method": "classify"},
        ],
    }


class TestDetectPipelineVersion:
    def test_v13_pipeline_detected(self) -> None:
        assert detect_pipeline_version(_v13_email_pipeline()) == "v1.3"

    def test_v14_pipeline_by_version_field(self) -> None:
        assert detect_pipeline_version(_v14_pipeline()) == "v1.4"

    def test_v14_pipeline_by_intake_normalize_step(self) -> None:
        pipeline = {
            "name": "test",
            "steps": [
                {"name": "intake", "adapter": "intake_normalize"},
                {"name": "process", "adapter": "doc_adapter"},
            ],
        }
        assert detect_pipeline_version(pipeline) == "v1.4"

    def test_empty_pipeline_defaults_to_v13(self) -> None:
        assert detect_pipeline_version({}) == "v1.3"

    def test_empty_steps_defaults_to_v13(self) -> None:
        assert detect_pipeline_version({"steps": []}) == "v1.3"

    def test_version_prefix_check(self) -> None:
        assert detect_pipeline_version({"version": "2.1"}) == "v1.4"
        assert detect_pipeline_version({"version": "1.3"}) == "v1.3"

    def test_no_email_pipeline_is_v13(self) -> None:
        assert detect_pipeline_version(_v13_no_email_pipeline()) == "v1.3"


class TestUpgradePipelineV13ToV14:
    def test_sets_version_to_2_0(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_email_pipeline())
        assert result["version"] == "2.0"

    def test_email_adapter_becomes_intake_normalize(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_email_pipeline())
        intake_step = result["steps"][0]
        assert intake_step["adapter"] == "intake_normalize"
        assert intake_step["config"]["source_type"] == "email"
        assert intake_step["config"]["source_config"] == {"folder": "INBOX"}

    def test_document_adapter_extract_becomes_extract_from_package(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_email_pipeline())
        doc_step = next(s for s in result["steps"] if s.get("adapter") == "document_adapter")
        assert doc_step["method"] == "extract_from_package"

    def test_for_each_rewritten_to_package(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_email_pipeline())
        doc_step = next(s for s in result["steps"] if s.get("adapter") == "document_adapter")
        assert doc_step["for_each"] == "{{ intake.output.package }}"

    def test_passthrough_for_unknown_steps(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_email_pipeline())
        notify_step = next(s for s in result["steps"] if s.get("name") == "notify")
        assert notify_step["adapter"] == "notification_adapter"
        assert notify_step["method"] == "send"

    def test_preserves_existing_v14_pipeline(self) -> None:
        original = _v14_pipeline()
        result = upgrade_pipeline_v1_3_to_v1_4(original)
        assert result["version"] == "2.0"
        assert len(result["steps"]) == len(original["steps"])

    def test_handles_empty_steps(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4({"name": "empty", "steps": []})
        assert result["steps"] == []
        assert result["version"] == "2.0"

    def test_does_not_mutate_input(self) -> None:
        original = _v13_email_pipeline()
        original_steps_count = len(original["steps"])
        upgrade_pipeline_v1_3_to_v1_4(original)
        assert len(original["steps"]) == original_steps_count
        assert "version" not in original

    def test_no_email_pipeline_passthrough(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_no_email_pipeline())
        assert result["version"] == "2.0"
        assert len(result["steps"]) == 2
        assert result["steps"][0]["adapter"] == "parser_adapter"
        assert result["steps"][1]["adapter"] == "classifier_adapter"

    def test_preserves_pipeline_name(self) -> None:
        result = upgrade_pipeline_v1_3_to_v1_4(_v13_email_pipeline())
        assert result["name"] == "invoice_email_pipeline"
