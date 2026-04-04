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

from aiflow.core.config import AIFlowSettings, get_settings


class TestAIFlowSettings:
    def test_default_values(self):
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
