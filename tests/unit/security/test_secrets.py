"""
@test_registry:
    suite: security-unit
    component: security.secrets
    covers: [src/aiflow/security/secrets.py]
    phase: 7
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [security, secrets, env, vault]
"""
import pytest
from aiflow.security.secrets import SecretProvider, EnvSecretProvider, SecretManager


class TestEnvSecretProvider:
    def test_get_from_env(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_SECRET_DB_PASS", "super-secret-value")
        provider = EnvSecretProvider()
        value = provider.get_secret("db_pass")
        assert value == "super-secret-value"

    def test_missing_key_returns_none(self, monkeypatch):
        monkeypatch.delenv("AIFLOW_SECRET_NONEXISTENT", raising=False)
        provider = EnvSecretProvider()
        value = provider.get_secret("nonexistent")
        assert value is None

    def test_implements_secret_provider(self):
        provider = EnvSecretProvider()
        assert isinstance(provider, SecretProvider)

    def test_set_and_get_round_trip(self, monkeypatch):
        provider = EnvSecretProvider()
        provider.set_secret("round_trip", "hello")
        assert provider.get_secret("round_trip") == "hello"
        # Clean up
        monkeypatch.delenv("AIFLOW_SECRET_ROUND_TRIP", raising=False)

    def test_list_keys(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_SECRET_KEY_A", "a")
        monkeypatch.setenv("AIFLOW_SECRET_KEY_B", "b")
        provider = EnvSecretProvider()
        keys = provider.list_keys()
        assert "key_a" in keys
        assert "key_b" in keys


class TestSecretManager:
    @pytest.fixture
    def manager(self):
        provider = EnvSecretProvider(prefix="TEST_SM_")
        return SecretManager(provider=provider, cache_ttl_seconds=60.0)

    def test_set_and_get(self, manager, monkeypatch):
        manager.set_secret("db_password", "s3cret")
        assert manager.get_secret("db_password") == "s3cret"

    def test_get_missing_returns_none(self, manager, monkeypatch):
        monkeypatch.delenv("TEST_SM_MISSING_KEY", raising=False)
        assert manager.get_secret("missing_key") is None

    def test_delete_key(self, manager):
        manager.set_secret("api_key", "abc123")
        manager.delete_secret("api_key")
        assert manager.get_secret("api_key") is None

    def test_list_keys(self, manager):
        manager.set_secret("key_x", "val_x")
        manager.set_secret("key_y", "val_y")
        keys = manager.list_keys()
        assert "key_x" in keys
        assert "key_y" in keys

    def test_caching_returns_same_value(self, manager):
        manager.set_secret("cached_key", "cached_val")
        val1 = manager.get_secret("cached_key")
        val2 = manager.get_secret("cached_key")
        assert val1 == val2 == "cached_val"

    def test_overwrite_existing_key(self, manager):
        manager.set_secret("key", "original")
        manager.set_secret("key", "updated")
        assert manager.get_secret("key") == "updated"

    def test_invalidate_cache(self, manager):
        manager.set_secret("inv_key", "value")
        assert manager.get_secret("inv_key") == "value"
        manager.invalidate_cache("inv_key")
        # Still returns the value from provider (not cache)
        assert manager.get_secret("inv_key") == "value"
