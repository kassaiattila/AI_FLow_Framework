"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.builtin_templates
    covers: [src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml]
    phase: B3
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [pipeline, template, invoice-finder, v3]
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aiflow.pipeline.parser import PipelineParser
from aiflow.pipeline.schema import PipelineDefinition

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "aiflow"
    / "pipeline"
    / "builtin_templates"
    / "invoice_finder_v3.yaml"
)


@pytest.fixture(scope="module")
def yaml_source() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pipeline_def(yaml_source: str) -> PipelineDefinition:
    parser = PipelineParser()
    return parser.parse_yaml(yaml_source)


class TestInvoiceFinderV3Template:
    """Pipeline YAML validation tests for invoice_finder_v3."""

    def test_file_exists_and_valid_yaml(self, yaml_source: str) -> None:
        """Template file exists and is valid YAML with required top-level keys."""
        assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"
        data = yaml.safe_load(yaml_source)
        assert isinstance(data, dict)
        assert "name" in data
        assert "steps" in data
        assert data["name"] == "invoice_finder_v3"
        assert data["version"] == "3.0.0"

    def test_parses_with_correct_metadata(self, pipeline_def: PipelineDefinition) -> None:
        """Pipeline parses without error and has correct name/version/trigger."""
        assert pipeline_def.name == "invoice_finder_v3"
        assert pipeline_def.version == "3.0.0"
        assert pipeline_def.trigger.type.value == "manual"
        assert "connector_id" in pipeline_def.input_schema
        assert "days" in pipeline_def.input_schema
        assert "confidence_threshold" in pipeline_def.input_schema
        assert pipeline_def.metadata.get("cycle") == "B3"

    def test_has_eight_steps_in_correct_order(self, pipeline_def: PipelineDefinition) -> None:
        """Pipeline defines exactly 8 steps with correct names and ordering."""
        names = pipeline_def.step_names()
        assert len(names) == 8
        expected = [
            "search_emails",
            "acquire_documents",
            "classify_invoices",
            "extract_fields",
            "check_payment_status",
            "organize_files",
            "generate_report",
            "notify_team",
        ]
        assert names == expected

    def test_step_dependencies_form_valid_dag(self, pipeline_def: PipelineDefinition) -> None:
        """Step dependencies form a valid DAG (no cycles, all refs exist)."""
        step_names = set(pipeline_def.step_names())

        # search_emails has no dependencies (entry point)
        search = pipeline_def.get_step("search_emails")
        assert search is not None
        assert search.depends_on == []

        # acquire_documents depends on search_emails
        acquire = pipeline_def.get_step("acquire_documents")
        assert acquire is not None
        assert "search_emails" in acquire.depends_on

        # classify depends on acquire
        classify = pipeline_def.get_step("classify_invoices")
        assert classify is not None
        assert "acquire_documents" in classify.depends_on

        # extract depends on classify and acquire
        extract = pipeline_def.get_step("extract_fields")
        assert extract is not None
        assert "classify_invoices" in extract.depends_on
        assert "acquire_documents" in extract.depends_on

        # notify is the terminal step
        notify = pipeline_def.get_step("notify_team")
        assert notify is not None
        assert "generate_report" in notify.depends_on

        # All dependency references point to existing steps
        for step in pipeline_def.steps:
            for dep in step.depends_on:
                assert dep in step_names, f"Step '{step.name}' depends on unknown '{dep}'"

    def test_b31_steps_have_correct_service_method(self, pipeline_def: PipelineDefinition) -> None:
        """B3.1 steps (search, acquire, classify) map to correct service/method pairs."""
        search = pipeline_def.get_step("search_emails")
        assert search is not None
        assert search.service == "email_connector"
        assert search.method == "search_invoices"
        assert search.timeout == 120

        acquire = pipeline_def.get_step("acquire_documents")
        assert acquire is not None
        assert acquire.service == "document_extractor"
        assert acquire.method == "acquire_from_email"
        assert acquire.for_each is not None
        assert acquire.concurrency == 3

        classify = pipeline_def.get_step("classify_invoices")
        assert classify is not None
        assert classify.service == "classifier"
        assert classify.method == "classify"
        assert classify.for_each is not None
        assert classify.concurrency == 5
