"""
@test_registry:
    suite: integration-api
    component: api.v1.runs.trace_proxy
    covers:
        - src/aiflow/api/v1/runs.py (get_run_trace + _build_trace_tree)
        - src/aiflow/api/v1/monitoring.py (span-metrics aggregate)
    phase: 1d
    priority: critical
    estimated_duration_ms: 2000
    requires_services: []
    tags: [integration, api, runs, monitoring, uc_monitoring, sprint_l, s111]

Sprint L S111 — Langfuse trace proxy + span-metrics aggregate.

Three scenarios per replan §4:
  - happy path (run has trace_id, Langfuse returns a tree with one generation)
  - missing trace_id on run → 404
  - Langfuse API failure → 502

The backend is exercised via FastAPI TestClient. The Langfuse client and the
DB pool are stubbed at module level so the tests stay hermetic (no Postgres /
no network).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from aiflow.api.v1 import monitoring as monitoring_mod
from aiflow.api.v1 import runs as runs_mod
from aiflow.security.auth import AuthProvider

_shared_auth = AuthProvider.from_env()

from aiflow.api.app import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def _patch_auth_from_env():
    with patch.object(AuthProvider, "from_env", return_value=_shared_auth):
        yield


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_header() -> dict[str, str]:
    token = _shared_auth.create_token(user_id="test-admin", role="admin", team_id="default")
    return {"Authorization": f"Bearer {token}"}


class _FakePoolAcquire:
    def __init__(self, conn: object) -> None:
        self._conn = conn

    async def __aenter__(self) -> object:
        return self._conn

    async def __aexit__(self, *_: object) -> None:
        return None


class _FakePool:
    def __init__(self, conn: object) -> None:
        self._conn = conn

    def acquire(self) -> _FakePoolAcquire:
        return _FakePoolAcquire(self._conn)


class _FakeConn:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    async def fetchrow(self, _sql: str, *_params: object) -> dict | None:
        return self._row


def _patch_pool(row: dict | None):
    async def _get_pool() -> _FakePool:
        return _FakePool(_FakeConn(row))

    return patch.object(runs_mod, "get_pool", _get_pool)


def _fake_trace_obj() -> SimpleNamespace:
    start = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    root = SimpleNamespace(
        id="obs_root",
        parent_observation_id=None,
        trace_id="t_1",
        type="SPAN",
        name="workflow_run",
        start_time=start,
        end_time=start + timedelta(milliseconds=500),
        model=None,
        usage=SimpleNamespace(input=0, output=0, total=0),
        usage_details={},
        cost_details={},
        calculated_total_cost=None,
        latency=0.5,
        level=SimpleNamespace(value="DEFAULT"),
        status_message=None,
    )
    gen = SimpleNamespace(
        id="obs_gen",
        parent_observation_id="obs_root",
        trace_id="t_1",
        type="GENERATION",
        name="classifier.classify",
        start_time=start + timedelta(milliseconds=50),
        end_time=start + timedelta(milliseconds=450),
        model="gpt-4o-mini",
        usage=SimpleNamespace(input=120, output=40, total=160),
        usage_details={"input": 120, "output": 40},
        cost_details={"input": 0.0002, "output": 0.0001},
        calculated_total_cost=0.0003,
        latency=0.4,
        level=SimpleNamespace(value="DEFAULT"),
        status_message=None,
    )
    return SimpleNamespace(
        id="t_1",
        name="acme.classifier",
        latency=0.5,
        total_cost=0.0003,
        observations=[root, gen],
    )


def test_get_run_trace_happy_path(client: TestClient, auth_header: dict[str, str]) -> None:
    row = {"trace_id": "t_1"}
    fake_client = SimpleNamespace(
        api=SimpleNamespace(trace=SimpleNamespace(get=lambda _tid: _fake_trace_obj()))
    )
    with (
        _patch_pool(row),
        patch.object(runs_mod, "get_langfuse_client", return_value=fake_client),
    ):
        r = client.get(
            "/api/v1/runs/00000000-0000-0000-0000-000000000001/trace",
            headers=auth_header,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trace_id"] == "t_1"
    assert body["run_id"] == "00000000-0000-0000-0000-000000000001"
    assert body["total_duration_ms"] == 500
    assert body["total_cost_usd"] == pytest.approx(0.0003, rel=1e-6)
    assert body["source"] == "backend"
    assert len(body["root_spans"]) == 1
    root = body["root_spans"][0]
    assert root["name"] == "workflow_run"
    assert root["duration_ms"] == 500
    assert len(root["children"]) == 1
    child = root["children"][0]
    assert child["name"] == "classifier.classify"
    assert child["model"] == "gpt-4o-mini"
    assert child["input_tokens"] == 120
    assert child["output_tokens"] == 40
    assert child["cost_usd"] == pytest.approx(0.0003, rel=1e-6)
    assert child["start_ms"] == 50
    assert child["duration_ms"] == 400


def test_get_run_trace_missing_trace_id(client: TestClient, auth_header: dict[str, str]) -> None:
    row = {"trace_id": None}
    with _patch_pool(row):
        r = client.get(
            "/api/v1/runs/00000000-0000-0000-0000-000000000002/trace",
            headers=auth_header,
        )
    assert r.status_code == 404
    assert "no trace_id" in r.json()["detail"].lower()


def test_get_run_trace_langfuse_error(client: TestClient, auth_header: dict[str, str]) -> None:
    row = {"trace_id": "t_boom"}

    def _boom(_tid: str) -> object:
        raise RuntimeError("langfuse http 500")

    fake_client = SimpleNamespace(api=SimpleNamespace(trace=SimpleNamespace(get=_boom)))
    with (
        _patch_pool(row),
        patch.object(runs_mod, "get_langfuse_client", return_value=fake_client),
    ):
        r = client.get(
            "/api/v1/runs/00000000-0000-0000-0000-000000000003/trace",
            headers=auth_header,
        )
    assert r.status_code == 502
    assert "langfuse fetch failed" in r.json()["detail"].lower()


def test_span_metrics_happy_path(client: TestClient, auth_header: dict[str, str]) -> None:
    start = datetime.now(UTC) - timedelta(hours=1)
    obs_a = SimpleNamespace(
        model="gpt-4o-mini",
        start_time=start,
        end_time=start + timedelta(milliseconds=200),
        latency=0.2,
        usage=SimpleNamespace(input=100, output=50, total=150),
        usage_details={"input": 100, "output": 50},
        cost_details={"input": 0.0001, "output": 0.0001},
        calculated_total_cost=0.0002,
    )
    obs_b = SimpleNamespace(
        model="gpt-4o-mini",
        start_time=start + timedelta(minutes=1),
        end_time=start + timedelta(minutes=1, milliseconds=600),
        latency=0.6,
        usage=SimpleNamespace(input=200, output=80, total=280),
        usage_details={"input": 200, "output": 80},
        cost_details={},
        calculated_total_cost=0.0005,
    )
    obs_c = SimpleNamespace(
        model="text-embedding-3-small",
        start_time=start + timedelta(minutes=2),
        end_time=start + timedelta(minutes=2, milliseconds=50),
        latency=0.05,
        usage=SimpleNamespace(input=500, output=0, total=500),
        usage_details={"input": 500},
        cost_details={},
        calculated_total_cost=0.00001,
    )
    page = SimpleNamespace(data=[obs_a, obs_b, obs_c])
    fake_client = SimpleNamespace(
        api=SimpleNamespace(observations=SimpleNamespace(get_many=lambda **_kw: page))
    )
    with patch.object(monitoring_mod, "get_langfuse_client", return_value=fake_client):
        r = client.get("/api/v1/monitoring/span-metrics?window_h=24", headers=auth_header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_spans"] == 3
    assert body["window_h"] == 24
    models = {m["model"]: m for m in body["models"]}
    assert "gpt-4o-mini" in models and "text-embedding-3-small" in models
    gpt = models["gpt-4o-mini"]
    assert gpt["span_count"] == 2
    assert gpt["total_input_tokens"] == 300
    assert gpt["total_output_tokens"] == 130
    assert gpt["total_cost_usd"] == pytest.approx(0.0007, rel=1e-6)
    assert gpt["avg_duration_ms"] == pytest.approx(400.0, rel=1e-3)
    # p95 with two points resolves to the higher one
    assert gpt["p95_duration_ms"] == pytest.approx(600.0, rel=1e-3)


def test_span_metrics_langfuse_unconfigured(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    with patch.object(monitoring_mod, "get_langfuse_client", return_value=None):
        r = client.get("/api/v1/monitoring/span-metrics", headers=auth_header)
    assert r.status_code == 503
    assert "langfuse not configured" in r.json()["detail"].lower()
