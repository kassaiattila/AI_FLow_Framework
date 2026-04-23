"""
@test_registry:
    suite: core-unit
    component: security.resolver
    covers: [src/aiflow/security/resolver.py, src/aiflow/security/secrets.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [security, vault, resolver, s117]
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from aiflow.core.config import AIFlowSettings, VaultSettings
from aiflow.security.resolver import (
    build_secret_manager,
    get_secret_manager,
    reset_secret_manager,
)
from aiflow.security.secrets import EnvSecretProvider, SecretManager


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Strip AIFLOW_VAULT__* + the alias env vars used in the tests."""
    for key in list(os.environ):
        if key.startswith("AIFLOW_VAULT__"):
            monkeypatch.delenv(key, raising=False)
    for alias in ("OPENAI_API_KEY", "AIFLOW_DATABASE__URL", "AIFLOW_WEBHOOK_HMAC_SECRET"):
        monkeypatch.delenv(alias, raising=False)
    reset_secret_manager()
    yield
    reset_secret_manager()


class TestBuildSecretManagerDisabled:
    def test_returns_env_only_when_disabled(self):
        settings = AIFlowSettings(vault=VaultSettings(enabled=False))
        mgr = build_secret_manager(settings)
        assert isinstance(mgr, SecretManager)
        # No fallback because primary is already env in disabled mode.
        assert mgr._fallback is None  # noqa: SLF001
        assert isinstance(mgr._provider, EnvSecretProvider)  # noqa: SLF001

    def test_env_alias_resolves_through_primary(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-abc")
        settings = AIFlowSettings(vault=VaultSettings(enabled=False))
        mgr = build_secret_manager(settings)
        value = mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY")
        assert value == "sk-test-abc"

    def test_missing_secret_returns_none(self):
        settings = AIFlowSettings(vault=VaultSettings(enabled=False))
        mgr = build_secret_manager(settings)
        assert mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY") is None


class TestBuildSecretManagerEnabled:
    def test_token_auth_path(self):
        settings = AIFlowSettings(
            vault=VaultSettings(
                enabled=True,
                url="http://vault.test:8200",
                token="hvs.test-token",  # type: ignore[arg-type]
            )
        )
        with patch("aiflow.security.resolver.VaultSecretProvider") as vault_cls:
            mgr = build_secret_manager(settings)
        vault_cls.assert_called_once()
        kwargs = vault_cls.call_args.kwargs
        assert kwargs["vault_url"] == "http://vault.test:8200"
        assert kwargs["token"] == "hvs.test-token"
        assert kwargs["role_id"] is None
        assert kwargs["secret_id"] is None
        assert kwargs["mount_point"] == "secret"
        assert kwargs["kv_namespace"] == "aiflow"
        assert isinstance(mgr._fallback, EnvSecretProvider)  # noqa: SLF001

    def test_approle_auth_path(self):
        settings = AIFlowSettings(
            vault=VaultSettings(
                enabled=True,
                url="http://vault.test:8200",
                role_id="role-a",
                secret_id="s-x",  # type: ignore[arg-type]
            )
        )
        with patch("aiflow.security.resolver.VaultSecretProvider") as vault_cls:
            build_secret_manager(settings)
        kwargs = vault_cls.call_args.kwargs
        assert kwargs["role_id"] == "role-a"
        assert kwargs["secret_id"] == "s-x"
        assert kwargs["token"] is None

    def test_env_fallback_triggers_on_vault_miss(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-fallback-value")
        settings = AIFlowSettings(
            vault=VaultSettings(enabled=True, token="hvs.t"),  # type: ignore[arg-type]
        )

        class _StubVault:
            def get_secret(self, key):  # noqa: D401, ARG002
                return None

            def set_secret(self, key, value):  # noqa: ARG002
                pass

            def delete_secret(self, key):  # noqa: ARG002
                pass

            def list_keys(self):
                return []

        with patch("aiflow.security.resolver.VaultSecretProvider", return_value=_StubVault()):
            mgr = build_secret_manager(settings)
        value = mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY")
        assert value == "env-fallback-value"


class TestGetSecretManagerSingleton:
    def test_is_cached(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_VAULT__ENABLED", "false")
        from aiflow.core.config import get_settings

        get_settings.cache_clear()
        m1 = get_secret_manager()
        m2 = get_secret_manager()
        assert m1 is m2

    def test_reset_clears_cache(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_VAULT__ENABLED", "false")
        from aiflow.core.config import get_settings

        get_settings.cache_clear()
        m1 = get_secret_manager()
        reset_secret_manager()
        m2 = get_secret_manager()
        assert m1 is not m2


class TestSecretManagerEnvAlias:
    def test_fallback_uses_env_alias(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-fallback")

        class _AlwaysMiss:
            def get_secret(self, key):  # noqa: ARG002
                return None

            def set_secret(self, key, value):  # noqa: ARG002
                pass

            def delete_secret(self, key):  # noqa: ARG002
                pass

            def list_keys(self):
                return []

        mgr = SecretManager(provider=_AlwaysMiss(), fallback=EnvSecretProvider(prefix=""))
        assert mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY") == "env-fallback"

    def test_no_env_alias_backward_compat(self, monkeypatch):
        monkeypatch.setenv("SOME_KEY", "direct")
        mgr = SecretManager(provider=EnvSecretProvider(prefix=""))
        assert mgr.get_secret("SOME_KEY") == "direct"
