"""
@test_registry:
    suite: pipeline-unit
    component: api.v1.pipelines.run
    covers: [src/aiflow/api/v1/pipelines.py]
    phase: C6
    priority: critical
    estimated_duration_ms: 150
    requires_services: []
    tags: [pipeline, api, run, endpoint]
"""

from __future__ import annotations

import pytest

from aiflow.api.v1.pipelines import (
    RunDetailResponse,
    RunItem,
    RunListResponse,
    RunPipelineRequest,
    RunPipelineResponse,
)


class TestRunPipelineRequest:
    def test_default_empty_input(self):
        req = RunPipelineRequest()
        assert req.input_data == {}

    def test_with_input_data(self):
        req = RunPipelineRequest(input_data={"connector_id": "cfg-1", "days": 7})
        assert req.input_data["connector_id"] == "cfg-1"
        assert req.input_data["days"] == 7

    def test_serialization_roundtrip(self):
        req = RunPipelineRequest(input_data={"key": "value"})
        dumped = req.model_dump()
        restored = RunPipelineRequest.model_validate(dumped)
        assert restored.input_data == {"key": "value"}


class TestRunPipelineResponse:
    def test_required_fields(self):
        resp = RunPipelineResponse(
            run_id="abc-123",
            pipeline_id="def-456",
            pipeline_name="test_pipe",
            status="completed",
        )
        assert resp.run_id == "abc-123"
        assert resp.pipeline_id == "def-456"
        assert resp.pipeline_name == "test_pipe"
        assert resp.status == "completed"
        assert resp.source == "backend"

    def test_source_default(self):
        resp = RunPipelineResponse(
            run_id="x",
            pipeline_id="y",
            pipeline_name="z",
            status="running",
        )
        assert resp.source == "backend"

    def test_failed_status(self):
        resp = RunPipelineResponse(
            run_id="x",
            pipeline_id="y",
            pipeline_name="z",
            status="failed",
        )
        assert resp.status == "failed"


class TestRunDetailResponse:
    def test_minimal(self):
        resp = RunDetailResponse(id="run-1")
        assert resp.id == "run-1"
        assert resp.status == ""
        assert resp.input_data == {}
        assert resp.steps == []
        assert resp.source == "backend"

    def test_with_steps(self):
        resp = RunDetailResponse(
            id="run-1",
            pipeline_id="pipe-1",
            workflow_name="invoice_automation_v1",
            status="completed",
            steps=[
                {"step_name": "fetch_emails", "status": "completed", "duration_ms": 100},
                {"step_name": "classify_intent", "status": "completed", "duration_ms": 200},
            ],
        )
        assert len(resp.steps) == 2
        assert resp.steps[0]["step_name"] == "fetch_emails"

    def test_with_error(self):
        resp = RunDetailResponse(
            id="run-1",
            status="failed",
            error="Step 'fetch_emails' failed: connection timeout",
        )
        assert resp.error is not None
        assert "timeout" in resp.error


class TestRunItemAndList:
    def test_run_item_defaults(self):
        item = RunItem(id="r-1")
        assert item.pipeline_id is None
        assert item.status == ""

    def test_run_list_response(self):
        items = [RunItem(id="r-1", status="completed"), RunItem(id="r-2", status="failed")]
        resp = RunListResponse(runs=items, total=2)
        assert resp.total == 2
        assert resp.source == "backend"
        assert len(resp.runs) == 2


class TestEndpointRegistration:
    def test_run_endpoint_exists_in_router(self):
        from aiflow.api.v1.pipelines import router

        paths = [route.path for route in router.routes]
        # Router includes prefix /api/v1/pipelines
        assert "/api/v1/pipelines/{pipeline_id}/run" in paths

    def test_run_endpoint_is_post(self):
        from aiflow.api.v1.pipelines import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/api/v1/pipelines/{pipeline_id}/run":
                assert "POST" in route.methods
                break
        else:
            pytest.fail("POST /api/v1/pipelines/{pipeline_id}/run route not found")
