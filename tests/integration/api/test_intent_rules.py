"""
@test_registry:
    suite: integration-api
    component: api.v1.emails.intent_rules
    covers:
        - src/aiflow/api/v1/emails.py (intent-rules endpoints)
        - src/aiflow/policy/intent_routing.py
    phase: 1d
    priority: critical
    estimated_duration_ms: 3000
    requires_services: [postgres]
    tags: [integration, api, emails, intent_rules, uc3, sprint_k, s109a]

UC3 Sprint K S109a — intent routing rules CRUD endpoints.
Covers list / get / upsert / delete against a real filesystem $POLICY_DIR.
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
def policy_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AIFLOW_POLICY_DIR", str(tmp_path))
    return tmp_path / "intent_routing"


@pytest.fixture
def client(policy_dir: Path) -> TestClient:  # noqa: ARG001  # triggers env patch
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_header() -> dict[str, str]:
    token = _shared_auth.create_token(user_id="test-admin", role="admin", team_id="default")
    return {"Authorization": f"Bearer {token}"}


def _valid_yaml(tenant_id: str = "acme") -> str:
    return (
        f"tenant_id: {tenant_id}\n"
        "default_action: manual_review\n"
        "default_target: inbox\n"
        "rules:\n"
        "  - intent_label: invoice_question\n"
        "    action: extract\n"
        "    target: invoice_pipeline\n"
        "    min_confidence: 0.6\n"
    )


async def test_intent_rules_full_crud_roundtrip(
    client: TestClient, auth_header: dict[str, str], policy_dir: Path
) -> None:
    """list (empty) → upsert → list (1) → get → delete → list (empty again)."""

    # --- Initial list: empty directory
    r = client.get("/api/v1/emails/intent-rules", headers=auth_header)
    assert r.status_code == 200
    assert r.json() == {"rules": [], "total": 0, "source": "backend"}

    # --- Upsert new tenant policy
    r = client.put(
        "/api/v1/emails/intent-rules/acme",
        json={"yaml_text": _valid_yaml("acme")},
        headers=auth_header,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == "acme"
    assert body["default_action"] == "manual_review"
    assert body["default_target"] == "inbox"
    assert len(body["rules"]) == 1
    assert body["rules"][0]["intent_label"] == "invoice_question"

    # File actually on disk
    expected_path = policy_dir / "acme.yaml"
    assert expected_path.exists(), f"YAML not written at {expected_path}"

    # --- List now has 1 row
    r = client.get("/api/v1/emails/intent-rules", headers=auth_header)
    assert r.status_code == 200
    lst = r.json()
    assert lst["total"] == 1
    assert lst["rules"][0]["tenant_id"] == "acme"
    assert lst["rules"][0]["rule_count"] == 1
    assert lst["rules"][0]["default_action"] == "manual_review"

    # --- Get detail
    r = client.get("/api/v1/emails/intent-rules/acme", headers=auth_header)
    assert r.status_code == 200
    detail = r.json()
    assert detail["tenant_id"] == "acme"
    assert "invoice_question" in detail["yaml_text"]

    # --- Delete
    r = client.delete("/api/v1/emails/intent-rules/acme", headers=auth_header)
    assert r.status_code == 204
    assert not expected_path.exists()

    # --- List empty again, delete idempotent
    r = client.get("/api/v1/emails/intent-rules", headers=auth_header)
    assert r.json()["total"] == 0
    r = client.delete("/api/v1/emails/intent-rules/acme", headers=auth_header)
    assert r.status_code == 204


async def test_intent_rules_rejects_path_traversal_tenant_id(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """`../etc/passwd`-style tenant_id must return 400 before hitting disk."""
    r = client.get("/api/v1/emails/intent-rules/..%2Fescape", headers=auth_header)
    # FastAPI normalizes %2F so the path-parameter value ends up containing '/'
    # or '..', either of which must fail validation.
    assert r.status_code in (400, 404, 422)


async def test_intent_rules_rejects_tenant_id_mismatch(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """YAML tenant_id != URL tenant_id → 422."""
    r = client.put(
        "/api/v1/emails/intent-rules/acme",
        json={"yaml_text": _valid_yaml("OTHER")},
        headers=auth_header,
    )
    assert r.status_code == 422
    assert "tenant_id mismatch" in r.text


async def test_intent_rules_rejects_malformed_yaml(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Broken YAML → 422 with parse error."""
    r = client.put(
        "/api/v1/emails/intent-rules/acme",
        json={"yaml_text": "tenant_id: acme\n  broken: [unclosed"},
        headers=auth_header,
    )
    assert r.status_code == 422


async def test_intent_rules_rejects_invalid_action_enum(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Unknown action value → 422 (Pydantic validation)."""
    bad = "tenant_id: acme\ndefault_action: NOT_A_VALID_ACTION\nrules: []\n"
    r = client.put(
        "/api/v1/emails/intent-rules/acme",
        json={"yaml_text": bad},
        headers=auth_header,
    )
    assert r.status_code == 422
