"""
@test_registry:
    suite: security-integration
    component: security.resolver
    covers:
      - src/aiflow/security/resolver.py
      - src/aiflow/core/config.py
    phase: 7
    priority: high
    estimated_duration_ms: 3000
    requires_services: [vault]
    tags: [security, resolver, vault, integration, s117]
"""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("hvac")

import hvac  # noqa: E402

from aiflow.core.config import AIFlowSettings, VaultSettings  # noqa: E402
from aiflow.security.resolver import build_secret_manager  # noqa: E402

VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "aiflow-dev-root")

pytestmark = pytest.mark.skipif(
    VAULT_ADDR is None,
    reason="VAULT_ADDR not set; start aiflow-vault-dev and export VAULT_ADDR.",
)


@pytest.fixture
def _live_namespace(monkeypatch):
    """Unique KV namespace per test so runs are isolated."""
    ns = f"aiflow-resolver-{uuid.uuid4().hex[:8]}"
    for key in (
        "AIFLOW_VAULT__ENABLED",
        "AIFLOW_VAULT__URL",
        "AIFLOW_VAULT__TOKEN",
        "AIFLOW_VAULT__KV_NAMESPACE",
    ):
        monkeypatch.delenv(key, raising=False)
    yield ns
    # Cleanup
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    try:
        listing = client.secrets.kv.v2.list_secrets(mount_point="secret", path=ns)
        for key in listing["data"]["keys"]:
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                mount_point="secret", path=f"{ns}/{key.rstrip('/')}"
            )
    except hvac.exceptions.InvalidPath:
        pass


class TestResolverDisabledMode:
    def test_env_only_resolves_aliased_secret(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-envonly-xyz")
        settings = AIFlowSettings(vault=VaultSettings(enabled=False))
        mgr = build_secret_manager(settings)
        assert mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY") == "sk-envonly-xyz"


class TestResolverVaultEnabled:
    def test_vault_primary_hit(self, _live_namespace):
        client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        client.secrets.kv.v2.create_or_update_secret(
            mount_point="secret",
            path=f"{_live_namespace}/llm/openai",
            secret={"api_key": "sk-vault-primary"},
        )
        settings = AIFlowSettings(
            vault=VaultSettings(
                enabled=True,
                url=VAULT_ADDR,
                token=VAULT_TOKEN,  # type: ignore[arg-type]
                kv_namespace=_live_namespace,
            )
        )
        mgr = build_secret_manager(settings)
        assert (
            mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY") == "sk-vault-primary"
        )

    def test_vault_miss_falls_back_to_env(self, monkeypatch, _live_namespace):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-fallback")
        settings = AIFlowSettings(
            vault=VaultSettings(
                enabled=True,
                url=VAULT_ADDR,
                token=VAULT_TOKEN,  # type: ignore[arg-type]
                kv_namespace=_live_namespace,
            )
        )
        mgr = build_secret_manager(settings)
        # Vault has nothing seeded at this path → fallback via env_alias.
        assert mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY") == "sk-env-fallback"

    def test_all_miss_returns_none(self, monkeypatch, _live_namespace):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        settings = AIFlowSettings(
            vault=VaultSettings(
                enabled=True,
                url=VAULT_ADDR,
                token=VAULT_TOKEN,  # type: ignore[arg-type]
                kv_namespace=_live_namespace,
            )
        )
        mgr = build_secret_manager(settings)
        assert mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY") is None
