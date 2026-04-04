"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.builtin_templates
    covers: [src/aiflow/pipeline/builtin_templates/invoice_automation_v2.yaml]
    phase: C9
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, template, invoice, v2, notification, data-router]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.pipeline.adapter_base import AdapterRegistry
from aiflow.pipeline.compiler import PipelineCompiler
from aiflow.pipeline.parser import PipelineParser
from aiflow.pipeline.schema import PipelineDefinition

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "aiflow"
    / "pipeline"
    / "builtin_templates"
    / "invoice_automation_v2.yaml"
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
    from aiflow.pipeline.adapters.classifier_adapter import ClassifierAdapter
    from aiflow.pipeline.adapters.data_router_adapter import (
        DataRouterFilterAdapter,
        DataRouterRouteAdapter,
    )
    from aiflow.pipeline.adapters.document_adapter import DocumentExtractAdapter
    from aiflow.pipeline.adapters.email_adapter import EmailFetchAdapter
    from aiflow.pipeline.adapters.notification_adapter import NotificationSendAdapter

    reg.register(EmailFetchAdapter())
    reg.register(ClassifierAdapter())
    reg.register(DocumentExtractAdapter())
    reg.register(DataRouterFilterAdapter())
    reg.register(DataRouterRouteAdapter())
    reg.register(NotificationSendAdapter())
    return reg


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------


class TestV2TemplateFile:
    def test_file_exists(self) -> None:
        assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"

    def test_file_is_valid_yaml(self, yaml_source: str) -> None:
        import yaml

        data = yaml.safe_load(yaml_source)
        assert isinstance(data, dict)
        assert "name" in data
        assert "steps" in data


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestV2TemplateParsing:
    def test_parses_without_error(self, pipeline_def: PipelineDefinition) -> None:
        assert pipeline_def is not None

    def test_name_and_version(self, pipeline_def: PipelineDefinition) -> None:
        assert pipeline_def.name == "invoice_automation_v2"
        assert pipeline_def.version == "2.0.0"

    def test_description(self, pipeline_def: PipelineDefinition) -> None:
        assert "notify" in pipeline_def.description.lower()

    def test_trigger_is_manual(self, pipeline_def: PipelineDefinition) -> None:
        assert pipeline_def.trigger.type.value == "manual"

    def test_has_input_schema(self, pipeline_def: PipelineDefinition) -> None:
        assert "connector_id" in pipeline_def.input_schema
        assert "notify_channel" in pipeline_def.input_schema
        assert "notify_recipients" in pipeline_def.input_schema

    def test_has_five_steps(self, pipeline_def: PipelineDefinition) -> None:
        assert len(pipeline_def.steps) == 5

    def test_step_names(self, pipeline_def: PipelineDefinition) -> None:
        names = pipeline_def.step_names()
        assert "fetch_emails" in names
        assert "classify_intent" in names
        assert "extract_documents" in names
        assert "route_documents" in names
        assert "notify_team" in names

    def test_v1_steps_unchanged(self, pipeline_def: PipelineDefinition) -> None:
        fetch = pipeline_def.get_step("fetch_emails")
        assert fetch is not None
        assert fetch.service == "email_connector"
        assert fetch.method == "fetch_emails"

        classify = pipeline_def.get_step("classify_intent")
        assert classify is not None
        assert classify.service == "classifier"

        extract = pipeline_def.get_step("extract_documents")
        assert extract is not None
        assert extract.service == "document_extractor"

    def test_route_documents_step(self, pipeline_def: PipelineDefinition) -> None:
        route = pipeline_def.get_step("route_documents")
        assert route is not None
        assert route.service == "data_router"
        assert route.method == "filter"
        assert "extract_documents" in route.depends_on
        assert "classify_intent" in route.depends_on

    def test_notify_team_step(self, pipeline_def: PipelineDefinition) -> None:
        notify = pipeline_def.get_step("notify_team")
        assert notify is not None
        assert notify.service == "notification"
        assert notify.method == "send"
        assert "route_documents" in notify.depends_on

    def test_notify_has_retry(self, pipeline_def: PipelineDefinition) -> None:
        notify = pipeline_def.get_step("notify_team")
        assert notify is not None
        assert notify.retry is not None
        assert notify.retry.max_retries == 2

    def test_metadata(self, pipeline_def: PipelineDefinition) -> None:
        assert pipeline_def.metadata.get("cycle") == "C9"
        assert pipeline_def.metadata.get("tier") == "2"


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


class TestV2TemplateCompilation:
    def test_compiles_with_adapters(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ) -> None:
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        assert result is not None
        assert len(result.step_funcs) == 5

    def test_dag_is_valid(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ) -> None:
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        errors = result.dag.validate()
        assert errors == [] or errors is None or len(errors) == 0

    def test_dag_topological_order(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ) -> None:
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        order = result.dag.topological_sort()
        # V1 ordering preserved
        assert order.index("fetch_emails") < order.index("classify_intent")
        assert order.index("fetch_emails") < order.index("extract_documents")
        # V2 new steps come after their dependencies
        assert order.index("extract_documents") < order.index("route_documents")
        assert order.index("classify_intent") < order.index("route_documents")
        assert order.index("route_documents") < order.index("notify_team")

    def test_step_funcs_are_callable(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ) -> None:
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        for name, func in result.step_funcs.items():
            assert callable(func), f"Step func {name} is not callable"

    def test_all_adapters_resolved(
        self, pipeline_def: PipelineDefinition, registry: AdapterRegistry
    ) -> None:
        compiler = PipelineCompiler(registry)
        result = compiler.compile(pipeline_def)
        expected = {
            "fetch_emails",
            "classify_intent",
            "extract_documents",
            "route_documents",
            "notify_team",
        }
        assert set(result.step_funcs.keys()) == expected
