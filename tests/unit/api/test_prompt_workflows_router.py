"""
@test_registry:
    suite: api-unit
    component: api.prompt_workflows (Sprint R / S140)
    covers:
        - src/aiflow/api/v1/prompt_workflows.py
    phase: sprint-r-s140
    priority: high
    estimated_duration_ms: 3000
    requires_services: []
    tags: [api, prompts, workflows, sprint-r, s140]
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider

# Shared auth provider — must be active when Starlette builds its middleware
# stack on the first request.
_shared_auth = AuthProvider.from_env()
_from_env_patcher = patch.object(AuthProvider, "from_env", return_value=_shared_auth)
_from_env_patcher.start()

from aiflow.api.app import create_app  # noqa: E402 — must come after auth patch

_test_token = _shared_auth.create_token(user_id="s140-test", role="admin")
_AUTH_HEADERS = {"Authorization": f"Bearer {_test_token}"}


@pytest.fixture(autouse=True)
def _reset_singleton_and_settings_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Each test gets a fresh PromptManager + fresh settings cache."""
    import aiflow.api.v1.prompts as prompts_module
    from aiflow.core.config import get_settings

    prompts_module._prompt_manager = None
    get_settings.cache_clear()
    yield
    prompts_module._prompt_manager = None
    get_settings.cache_clear()


def _client(monkeypatch: pytest.MonkeyPatch, *, enabled: bool) -> TestClient:
    if enabled:
        monkeypatch.setenv("AIFLOW_PROMPT_WORKFLOWS__ENABLED", "true")
    else:
        monkeypatch.delenv("AIFLOW_PROMPT_WORKFLOWS__ENABLED", raising=False)

    from aiflow.core.config import get_settings

    get_settings.cache_clear()
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    # Warmup so middleware initializes against the shared AuthProvider.
    client.get("/health/live")
    return client


class TestFlagGating:
    def test_list_flag_off_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=False)
        resp = client.get("/api/v1/prompts/workflows", headers=_AUTH_HEADERS)
        assert resp.status_code == 503
        assert resp.json()["detail"]["error_code"] == "FEATURE_DISABLED"
        assert resp.json()["detail"]["feature"] == "prompt_workflows"

    def test_detail_flag_off_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=False)
        resp = client.get("/api/v1/prompts/workflows/anything", headers=_AUTH_HEADERS)
        assert resp.status_code == 503

    def test_dry_run_flag_off_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=False)
        resp = client.get("/api/v1/prompts/workflows/anything/dry-run", headers=_AUTH_HEADERS)
        assert resp.status_code == 503


class TestListing:
    def test_list_includes_repo_example(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        names = {wf["name"] for wf in body["workflows"]}
        assert "uc3_intent_and_extract" in names
        assert body["total"] == len(body["workflows"])
        assert body["source"] == "backend"

    def test_list_item_shape(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        items = resp.json()["workflows"]
        item = next(i for i in items if i["name"] == "uc3_intent_and_extract")
        assert set(item.keys()) >= {
            "name",
            "version",
            "step_count",
            "tags",
            "default_label",
        }
        assert item["step_count"] == 3
        assert item["default_label"] == "prod"

    def test_list_source_local_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Sprint W SW-4 (SR-FU-6) — `?source=local` matches default behaviour.
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows?source=local", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        names = {wf["name"] for wf in resp.json()["workflows"]}
        assert "uc3_intent_and_extract" in names

    def test_list_source_langfuse_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Stub helper returns []; router must respond 200 with zero rows.
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows?source=langfuse", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["workflows"] == []
        assert body["total"] == 0

    def test_list_source_both_dedupes_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # `both` merges local + langfuse; the stub langfuse list is empty,
        # so this returns the same set as `local`.
        client = _client(monkeypatch, enabled=True)
        resp_both = client.get("/api/v1/prompts/workflows?source=both", headers=_AUTH_HEADERS)
        resp_local = client.get("/api/v1/prompts/workflows?source=local", headers=_AUTH_HEADERS)
        names_both = {wf["name"] for wf in resp_both.json()["workflows"]}
        names_local = {wf["name"] for wf in resp_local.json()["workflows"]}
        assert names_both == names_local

    def test_list_source_invalid_returns_422(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows?source=badvalue", headers=_AUTH_HEADERS)
        assert resp.status_code == 422


class TestDetail:
    def test_detail_unknown_returns_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows/no_such_workflow", headers=_AUTH_HEADERS)
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "WORKFLOW_NOT_FOUND"

    def test_detail_known_returns_full_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows/uc3_intent_and_extract", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "uc3_intent_and_extract"
        assert len(body["steps"]) == 3
        ids = [s["id"] for s in body["steps"]]
        assert ids == ["classify", "extract_header", "extract_lines"]


class TestDryRun:
    def test_dry_run_unknown_returns_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get("/api/v1/prompts/workflows/no_such/dry-run", headers=_AUTH_HEADERS)
        assert resp.status_code == 404

    def test_dry_run_resolves_all_steps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get(
            "/api/v1/prompts/workflows/uc3_intent_and_extract/dry-run",
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["workflow"]["name"] == "uc3_intent_and_extract"
        assert set(body["steps"].keys()) == {
            "classify",
            "extract_header",
            "extract_lines",
        }
        for step_id, prompt in body["steps"].items():
            assert prompt.get("system") or prompt.get("user"), (
                f"step {step_id} resolved to an empty prompt"
            )
        assert body["resolved_label"] == "prod"

    def test_dry_run_label_override_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client(monkeypatch, enabled=True)
        resp = client.get(
            "/api/v1/prompts/workflows/uc3_intent_and_extract/dry-run?label=staging",
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["resolved_label"] == "staging"


def teardown_module() -> None:
    """Stop the AuthProvider patch — leak prevention for other test modules."""
    try:
        _from_env_patcher.stop()
    except RuntimeError:
        pass  # already stopped
