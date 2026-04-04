"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.runner
    covers: [src/aiflow/pipeline/runner.py, src/aiflow/pipeline/repository.py]
    phase: C3
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, runner, repository]
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from aiflow.pipeline.runner import PipelineRunResult
from aiflow.pipeline.schema import PipelineDefinition
from aiflow.state.models import PipelineDefinitionModel, WorkflowRunModel


# --- PipelineRunResult tests ---


class TestPipelineRunResult:
    def test_success_result(self):
        result = PipelineRunResult(
            run_id=uuid.uuid4(),
            pipeline_name="test",
            status="completed",
            step_outputs={"s1": {"result": "ok"}},
            total_duration_ms=150.0,
        )
        assert result.success is True
        assert result.status == "completed"
        assert result.error is None
        assert "test" in repr(result)

    def test_failed_result(self):
        result = PipelineRunResult(
            run_id=uuid.uuid4(),
            pipeline_name="test",
            status="failed",
            step_outputs={},
            total_duration_ms=50.0,
            error="Step 's1' failed: boom",
        )
        assert result.success is False
        assert result.error is not None

    def test_repr(self):
        r = PipelineRunResult(
            run_id=uuid.uuid4(),
            pipeline_name="my_pipe",
            status="completed",
            step_outputs={},
            total_duration_ms=0,
        )
        assert "my_pipe" in repr(r)
        assert "completed" in repr(r)


# --- PipelineDefinitionModel tests ---


class TestPipelineDefinitionModel:
    def test_model_creation(self):
        model = PipelineDefinitionModel(
            name="test_pipeline",
            version="1.0.0",
            yaml_source="name: test\nsteps: []",
            definition={"name": "test", "steps": []},
        )
        assert model.name == "test_pipeline"
        assert model.version == "1.0.0"
        # default=True only applies at DB level; Python-side is None until flush
        assert model.enabled is None or model.enabled is True

    def test_model_with_all_fields(self):
        tid = uuid.uuid4()
        model = PipelineDefinitionModel(
            name="full",
            version="2.0.0",
            description="Full pipeline",
            yaml_source="yaml here",
            definition={"name": "full", "steps": [{"name": "s1"}]},
            trigger_config={"type": "cron", "expression": "0 * * * *"},
            input_schema={"connector_id": {"type": "string"}},
            enabled=False,
            team_id=tid,
            created_by="admin",
        )
        assert model.description == "Full pipeline"
        assert model.enabled is False
        assert model.team_id == tid
        assert model.trigger_config["type"] == "cron"


# --- WorkflowRunModel pipeline_id FK tests ---


class TestWorkflowRunPipelineFK:
    def test_pipeline_id_field_exists(self):
        run = WorkflowRunModel(
            workflow_name="pipe_test",
            workflow_version="1.0.0",
            input_data={"key": "val"},
        )
        assert run.pipeline_id is None

    def test_pipeline_id_can_be_set(self):
        pid = uuid.uuid4()
        run = WorkflowRunModel(
            workflow_name="pipe_test",
            workflow_version="1.0.0",
            input_data={},
            pipeline_id=pid,
        )
        assert run.pipeline_id == pid


# --- PipelineDefinition → ORM roundtrip ---


class TestDefinitionRoundtrip:
    def test_definition_to_dict_and_back(self):
        yaml_def = {
            "name": "email_flow",
            "version": "1.0.0",
            "steps": [
                {
                    "name": "fetch",
                    "service": "email_connector",
                    "method": "fetch_emails",
                    "config": {"connector_id": "{{ input.cid }}"},
                },
                {
                    "name": "classify",
                    "service": "classifier",
                    "method": "classify",
                    "depends_on": ["fetch"],
                },
            ],
        }
        # Parse → dump → re-parse
        pipeline = PipelineDefinition.model_validate(yaml_def)
        dumped = pipeline.model_dump()
        restored = PipelineDefinition.model_validate(dumped)
        assert restored.name == "email_flow"
        assert len(restored.steps) == 2
        assert restored.steps[1].depends_on == ["fetch"]

    def test_model_stores_definition_as_dict(self):
        yaml_def = {
            "name": "test",
            "version": "1.0.0",
            "steps": [{"name": "s1", "service": "a", "method": "b"}],
        }
        pipeline = PipelineDefinition.model_validate(yaml_def)
        model = PipelineDefinitionModel(
            name=pipeline.name,
            version=pipeline.version,
            yaml_source="raw yaml",
            definition=pipeline.model_dump(),
        )
        # Restore from model
        restored = PipelineDefinition.model_validate(model.definition)
        assert restored.name == "test"
        assert restored.steps[0].service == "a"
