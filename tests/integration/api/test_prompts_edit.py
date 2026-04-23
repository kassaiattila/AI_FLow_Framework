"""
@test_registry:
    suite: integration-api
    component: api.v1.prompts.edit
    covers:
        - src/aiflow/api/v1/prompts.py (GET/PUT detail)
    phase: 1d
    priority: critical
    estimated_duration_ms: 2000
    requires_services: []
    tags: [integration, api, prompts, s109b]

Sprint K S109b — prompt detail/edit endpoints.
Uses an isolated $AIFLOW_PROMPT_DIRS fixture tree so production prompts
are never touched.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider

_shared_auth = AuthProvider.from_env()

from aiflow.api.app import create_app  # noqa: E402

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _patch_auth_from_env():
    with patch.object(AuthProvider, "from_env", return_value=_shared_auth):
        yield


@pytest.fixture
def prompt_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Isolated prompt root — list + detail + put all operate against this.
    root = tmp_path / "prompts"
    root.mkdir()
    sample = root / "demo_skill"
    sample.mkdir()
    # Seed one prompt file
    (sample / "greeter.yaml").write_text(
        "name: demo/greeter\n"
        'version: "1.0"\n'
        "system: |\n"
        "  You are a friendly greeter.\n"
        'user: "Say hi to {name}."\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AIFLOW_PROMPT_DIRS", str(root))
    return root


@pytest.fixture
def client(prompt_dir: Path) -> TestClient:  # noqa: ARG001
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_header() -> dict[str, str]:
    token = _shared_auth.create_token(user_id="test-admin", role="admin", team_id="default")
    return {"Authorization": f"Bearer {token}"}


async def test_prompt_detail_returns_yaml_text(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    r = client.get("/api/v1/prompts/demo/greeter", headers=auth_header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "demo/greeter"
    assert body["version"] == "1.0"
    assert "friendly greeter" in body["yaml_text"]


async def test_prompt_detail_404_unknown_name(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    r = client.get("/api/v1/prompts/does-not-exist", headers=auth_header)
    assert r.status_code == 404


async def test_prompt_upsert_writes_file_and_invalidates_cache(
    client: TestClient, auth_header: dict[str, str], prompt_dir: Path
) -> None:
    new_yaml = (
        "name: demo/greeter\n"
        'version: "1.1"\n'
        "system: |\n"
        "  You are a warm + helpful greeter.\n"
        'user: "Greet {name} in Hungarian."\n'
    )
    r = client.put(
        "/api/v1/prompts/demo/greeter",
        json={"yaml_text": new_yaml},
        headers=auth_header,
    )
    assert r.status_code == 200, r.text
    assert r.json()["version"] == "1.1"
    # Disk reflects the write
    on_disk = (prompt_dir / "demo_skill" / "greeter.yaml").read_text(encoding="utf-8")
    assert "warm + helpful greeter" in on_disk


async def test_prompt_upsert_rejects_name_mismatch(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    bad = 'name: demo/OTHER_NAME\nversion: "1.0"\nsystem: "x"\n'
    r = client.put(
        "/api/v1/prompts/demo/greeter",
        json={"yaml_text": bad},
        headers=auth_header,
    )
    assert r.status_code == 422
    assert "name mismatch" in r.text


async def test_prompt_upsert_rejects_malformed_yaml(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    r = client.put(
        "/api/v1/prompts/demo/greeter",
        json={"yaml_text": "name: demo/greeter\n[unclosed-list"},
        headers=auth_header,
    )
    assert r.status_code == 422
