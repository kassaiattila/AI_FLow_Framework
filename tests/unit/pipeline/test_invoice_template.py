"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.builtin_templates
    covers: [src/aiflow/pipeline/builtin_templates/invoice_automation_v1.yaml]
    phase: C6
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, template, invoice, yaml]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.pipeline.adapter_base import AdapterRegistry
from aiflow.pipeline.adapters import discover_adapters
from aiflow.pipeline.compiler import PipelineCompiler
from aiflow.pipeline.parser import PipelineParser
from aiflow.pipeline.schema import PipelineDefinition

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "aiflow"
    / "pipeline"
    / "builtin_templates"
    / "invoice_automation_v1.yaml"
)


@pytest.fixture(scope="module")
def yaml_source() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pipeline_def(yaml_source: str) -> PipelineDefinition:
    parser = PipelineParser()
    return parser.parse_yaml(yaml_source)


@pytest.fixture(scope="module")
def registry() -> AdapterRegistry:
    reg = AdapterRegistry()
    # Use the real adapters — tests that they are importable
    from aiflow.pipeline.adapters.email_adapter import EmailFetchAdapter
    from aiflow.pipeline.adapters.classifier_adapter import ClassifierAdapter
    from aiflow.pipeline.adapters.document_adapter import DocumentExtractAdapter

    reg.register(EmailFetchAdapter())
    reg.register(ClassifierAdapter())
    reg.register(DocumentExtractAdapter())
    return reg


class TestInvoiceTemplateFile:
    def test_file_exists(self):
        assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"

    def test_file_is_valid_yaml(self, yaml_source: str):
        import yaml

        data = yaml.safe_load(yaml_source)
        assert isinstance(data, dict)
        assert "name" in data
        assert "steps" in data


class TestInvoiceTemplateParsing:
    def test_parses_without_error(self, pipeline_def: PipelineDefinition):
        assert pipeline_def is not None

    def test_name_and_version(self, pipeline_def: PipelineDefinition):
        assert pipeline_def.name == "invoice_automation_v1"
        assert pipeline_def.version == "1.0.0"

    def test_description(self, pipeline_def: PipelineDefinition):
        assert "email" in pipeline_def.description.lower()

    def test_trigger_is_manual(self, pipeline_def: PipelineDefinition):
        assert pipeline_def.trigger.type.value == "manual"

    def test_has_input_schema(self, pipeline_def: PipelineDefinition):
        assert "connector_id" in pipeline_def.input_schema
        assert "days" in pipeline_def.input_schema

    def test_has_three_steps(self, pipeline_def: PipelineDefinition):
        assert len(pipeline_def.steps) == 3

    def test_step_names(self, pipeline_def: PipelineDefinition):
        names = pipeline_def.step_names()
        assert names == ["fetch_emails", "classify_intent", "extract_documents"]

    def test_step_services(self, pipeline_def: PipelineDefinition):
        services = [(s.service, s.method) for s in pipeline_def.steps]
        assert ("email_connector", "fetch_emails") in services
        assert ("classifier", "classify") in services
        assert ("document_extractor", "extract") in services

    def test_fetch_emails_has_no_deps(self, pipeline_def: PipelineDefinition):
        fetch = pipeline_def.get_step("fetch_emails")
        assert fetch is not None
        assert fetch.depends_on == []

    def test_classify_depends_on_fetch(self, pipeline_def: PipelineDefinition):
        classify = pipeline_def.get_step("classify_intent")
        assert classify is not None
        assert "fetch_emails" in classify.depends_on

    def test_extract_depends_on_fetch(self, pipeline_def: PipelineDefinition):
        extract = pipeline_def.get_step("extract_documents")
        assert extract is not None
        assert "fetch_emails" in extract.depends_on

    def test_classify_has_for_each(self, pipeline_def: PipelineDefinition):
        classify = pipeline_def.get_step("classify_intent")
        assert classify is not None
        assert classify.for_each is not None
        assert "emails" in classify.for_each

    def test_extract_has_for_each(self, pipeline_def: PipelineDefinition):
        extract = pipeline_def.get_step("extract_documents")
        assert extract is not None
        assert extract.for_each is not None

    def test_retry_policies(self, pipeline_def: PipelineDefinition):
        fetch = pipeline_def.get_step("fetch_emails")
        assert fetch is not None
        assert fetch.retry is not None
        assert fetch.retry.max_retries == 3

        classify = pipeline_def.get_step("classify_intent")
        assert classify is not None
        assert classify.retry is not None
        assert classify.retry.max_retries == 2

    def test_timeouts(self, pipeline_def: PipelineDefinition):
        fetch = pipeline_def.get_step("fetch_emails")
        assert fetch is not None
        assert fetch.timeout == 120

    def test_metadata(self, pipeline_def: PipelineDefinition):
        assert pipeline_def.metadata.get("cycle") == "C6"
        assert pipeline_def.metadata.get("tier") == "1.5"


class TestInvoiceTemplateCompilation:
    def test_compiles_with_adapters(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ):
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        assert result is not None
        assert len(result.step_funcs) == 3

    def test_dag_is_valid(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ):
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        errors = result.dag.validate()
        assert errors == [] or errors is None or len(errors) == 0

    def test_dag_topological_order(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ):
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        order = result.dag.topological_sort()
        # fetch_emails must come before classify and extract
        assert order.index("fetch_emails") < order.index("classify_intent")
        assert order.index("fetch_emails") < order.index("extract_documents")

    def test_step_funcs_are_callable(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ):
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        for name, func in result.step_funcs.items():
            assert callable(func), f"Step func {name} is not callable"
