"""
@test_registry:
    suite: core-unit
    component: core.config
    covers: [src/aiflow/core/config.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [config, settings, pydantic]
"""

import os

from aiflow.core.config import (
    AIFlowSettings,
    UC3AttachmentIntentSettings,
    VaultSettings,
    get_settings,
)


class TestAIFlowSettings:
    def test_default_values(self, monkeypatch):
        # Clean AIFLOW_ env vars that may leak from other tests
        # (e.g., create_app() calls load_dotenv() which sets AIFLOW_DEBUG=true)
        for key in list(os.environ):
            if key.startswith("AIFLOW_"):
                monkeypatch.delenv(key, raising=False)
        settings = AIFlowSettings()
        assert settings.environment == "dev"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.app_name == "aiflow"
        assert settings.version == "0.1.0"

    def test_database_defaults(self):
        settings = AIFlowSettings()
        assert "postgresql" in settings.database.url
        assert settings.database.pool_size == 20
        assert settings.database.echo is False

    def test_redis_defaults(self):
        settings = AIFlowSettings()
        assert "redis" in settings.redis.url
        assert settings.redis.prefix == "aiflow:"

    def test_security_defaults(self):
        settings = AIFlowSettings()
        assert settings.security.jwt_algorithm == "RS256"
        assert settings.security.jwt_access_token_ttl == 900
        assert settings.security.api_key_prefix == "aiflow_"

    def test_llm_defaults(self):
        settings = AIFlowSettings()
        assert "gpt-4o-mini" in settings.llm.default_model
        assert settings.llm.timeout == 30
        assert settings.llm.max_retries == 3

    def test_budget_defaults(self):
        settings = AIFlowSettings()
        assert settings.budget.default_per_run_usd == 10.0
        assert settings.budget.alert_threshold_pct == 80

    def test_is_production(self):
        settings = AIFlowSettings(environment="prod")
        assert settings.is_production is True
        settings_dev = AIFlowSettings(environment="dev")
        assert settings_dev.is_production is False

    def test_is_testing(self):
        settings = AIFlowSettings(environment="test")
        assert settings.is_testing is True

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_ENVIRONMENT", "staging")
        monkeypatch.setenv("AIFLOW_DEBUG", "true")
        settings = AIFlowSettings()
        assert settings.environment == "staging"
        assert settings.debug is True

    def test_nested_env_override(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_LLM__DEFAULT_MODEL", "anthropic/claude-sonnet-4-20250514")
        settings = AIFlowSettings()
        assert settings.llm.default_model == "anthropic/claude-sonnet-4-20250514"


class TestVaultSettings:
    def test_vault_defaults(self, monkeypatch):
        for key in list(os.environ):
            if key.startswith("AIFLOW_VAULT__"):
                monkeypatch.delenv(key, raising=False)
        settings = AIFlowSettings()
        assert settings.vault.enabled is False
        assert settings.vault.url == "http://localhost:8210"
        assert settings.vault.token is None
        assert settings.vault.role_id is None
        assert settings.vault.secret_id is None
        assert settings.vault.mount_point == "secret"
        assert settings.vault.kv_namespace == "aiflow"
        assert settings.vault.cache_ttl_seconds == 300.0
        assert settings.vault.negative_cache_ttl_seconds == 60.0

    def test_vault_env_override(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_VAULT__ENABLED", "true")
        monkeypatch.setenv("AIFLOW_VAULT__URL", "https://vault.example:8200")
        monkeypatch.setenv("AIFLOW_VAULT__TOKEN", "hvs.AAA")
        monkeypatch.setenv("AIFLOW_VAULT__KV_NAMESPACE", "tenant42")
        monkeypatch.setenv("AIFLOW_VAULT__CACHE_TTL_SECONDS", "120.5")
        settings = AIFlowSettings()
        assert settings.vault.enabled is True
        assert settings.vault.url == "https://vault.example:8200"
        assert settings.vault.token is not None
        assert settings.vault.token.get_secret_value() == "hvs.AAA"
        assert settings.vault.kv_namespace == "tenant42"
        assert settings.vault.cache_ttl_seconds == 120.5

    def test_vault_settings_direct(self):
        vs = VaultSettings(enabled=True, role_id="role-a", secret_id="s-x")
        assert vs.enabled is True
        assert vs.role_id == "role-a"
        assert vs.secret_id is not None
        assert vs.secret_id.get_secret_value() == "s-x"


class TestUC3AttachmentIntentSettings:
    def test_defaults(self, monkeypatch):
        for key in list(os.environ):
            if key.startswith("AIFLOW_UC3_ATTACHMENT_INTENT__"):
                monkeypatch.delenv(key, raising=False)
        settings = AIFlowSettings()
        assert settings.uc3_attachment_intent.enabled is False
        assert settings.uc3_attachment_intent.max_attachment_mb == 10
        assert settings.uc3_attachment_intent.total_budget_seconds == 5.0

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED", "true")
        monkeypatch.setenv("AIFLOW_UC3_ATTACHMENT_INTENT__MAX_ATTACHMENT_MB", "20")
        monkeypatch.setenv("AIFLOW_UC3_ATTACHMENT_INTENT__TOTAL_BUDGET_SECONDS", "8.5")
        settings = AIFlowSettings()
        assert settings.uc3_attachment_intent.enabled is True
        assert settings.uc3_attachment_intent.max_attachment_mb == 20
        assert settings.uc3_attachment_intent.total_budget_seconds == 8.5

    def test_direct_construction(self):
        cfg = UC3AttachmentIntentSettings(
            enabled=True, max_attachment_mb=5, total_budget_seconds=2.0
        )
        assert cfg.enabled is True
        assert cfg.max_attachment_mb == 5
        assert cfg.total_budget_seconds == 2.0


class TestGetSettings:
    def test_get_settings_returns_instance(self):
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, AIFlowSettings)

    def test_get_settings_is_cached(self):
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
