"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.schema
    covers: [src/aiflow/pipeline/schema.py]
    phase: C2
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, schema, pydantic]
"""

from __future__ import annotations

import pytest

from aiflow.pipeline.schema import (
    PipelineDefinition,
    PipelineStepDef,
    PipelineTriggerDef,
    StepRetryPolicy,
    TriggerType,
)


MINIMAL_PIPELINE = {
    "name": "test_pipeline",
    "steps": [
        {"name": "step1", "service": "email_connector", "method": "fetch_emails"}
    ],
}

FULL_PIPELINE = {
    "name": "email_to_document",
    "version": "1.0.0",
    "description": "Email processing pipeline",
    "trigger": {"type": "manual"},
    "input_schema": {"connector_id": {"type": "string", "required": True}},
    "steps": [
        {
            "name": "fetch_emails",
            "service": "email_connector",
            "method": "fetch_emails",
            "config": {"connector_id": "{{ input.connector_id }}"},
        },
        {
            "name": "classify",
            "service": "classifier",
            "method": "classify",
            "depends_on": ["fetch_emails"],
            "for_each": "{{ fetch_emails.output.emails }}",
            "config": {"text": "{{ item.subject }}"},
        },
        {
            "name": "extract",
            "service": "document_extractor",
            "method": "extract",
            "depends_on": ["classify"],
            "condition": "output.label == 'invoice'",
            "retry": {"max_retries": 2},
            "timeout": 30,
        },
    ],
    "metadata": {"author": "test"},
}


class TestPipelineStepDef:
    def test_minimal_step(self):
        step = PipelineStepDef(name="s1", service="svc", method="meth")
        assert step.name == "s1"
        assert step.depends_on == []
        assert step.for_each is None
        assert step.concurrency == 5

    def test_step_with_retry(self):
        step = PipelineStepDef(
            name="s1",
            service="svc",
            method="meth",
            retry=StepRetryPolicy(max_retries=2),
        )
        assert step.retry is not None
        assert step.retry.max_retries == 2

    def test_step_name_validation_empty(self):
        with pytest.raises(Exception):
            PipelineStepDef(name="", service="svc", method="m")

    def test_step_name_validation_special_chars(self):
        with pytest.raises(Exception):
            PipelineStepDef(name="step with space", service="svc", method="m")

    def test_step_name_allows_underscore_and_dash(self):
        step = PipelineStepDef(name="my-step_1", service="svc", method="m")
        assert step.name == "my-step_1"


class TestPipelineTriggerDef:
    def test_default_trigger(self):
        t = PipelineTriggerDef()
        assert t.type == TriggerType.MANUAL

    def test_cron_trigger(self):
        t = PipelineTriggerDef(type="cron", cron_expression="0 * * * *")
        assert t.type == TriggerType.CRON
        assert t.cron_expression == "0 * * * *"


class TestPipelineDefinition:
    def test_minimal_pipeline(self):
        p = PipelineDefinition.model_validate(MINIMAL_PIPELINE)
        assert p.name == "test_pipeline"
        assert len(p.steps) == 1
        assert p.version == "1.0.0"

    def test_full_pipeline(self):
        p = PipelineDefinition.model_validate(FULL_PIPELINE)
        assert p.name == "email_to_document"
        assert len(p.steps) == 3
        assert p.steps[1].for_each is not None
        assert p.steps[2].condition is not None
        assert p.steps[2].retry is not None
        assert p.metadata["author"] == "test"

    def test_empty_name_rejected(self):
        with pytest.raises(Exception):
            PipelineDefinition(name="", steps=[{"name": "s", "service": "a", "method": "b"}])

    def test_no_steps_rejected(self):
        with pytest.raises(Exception):
            PipelineDefinition(name="p", steps=[])

    def test_duplicate_step_names_rejected(self):
        with pytest.raises(Exception):
            PipelineDefinition.model_validate({
                "name": "p",
                "steps": [
                    {"name": "s1", "service": "a", "method": "b"},
                    {"name": "s1", "service": "c", "method": "d"},
                ],
            })

    def test_get_step(self):
        p = PipelineDefinition.model_validate(FULL_PIPELINE)
        assert p.get_step("fetch_emails") is not None
        assert p.get_step("nonexistent") is None

    def test_step_names(self):
        p = PipelineDefinition.model_validate(FULL_PIPELINE)
        assert p.step_names() == ["fetch_emails", "classify", "extract"]
