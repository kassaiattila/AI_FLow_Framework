"""AIFlow configuration using pydantic-settings.

Loads from: environment variables (AIFLOW_ prefix) > aiflow.yaml > defaults.
"""
from functools import lru_cache
from typing import Literal

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["AIFlowSettings", "get_settings"]

logger = structlog.get_logger(__name__)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIFLOW_DATABASE__")
    url: str = "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5432/aiflow_dev"
    pool_size: int = 20
    pool_overflow: int = 10
    echo: bool = False


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIFLOW_REDIS__")
    url: str = "redis://localhost:6379/0"
    prefix: str = "aiflow:"
    max_connections: int = 50


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIFLOW_SECURITY__")
    jwt_private_key_path: str = "./jwt_private.pem"
    jwt_public_key_path: str = "./jwt_public.pem"
    jwt_access_token_ttl: int = 900  # 15 minutes
    jwt_refresh_token_ttl: int = 604800  # 7 days
    jwt_algorithm: str = "RS256"
    api_key_prefix: str = "aiflow_"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIFLOW_LLM__")
    default_model: str = "openai/gpt-4o-mini"
    fallback_model: str = "openai/gpt-4o"
    timeout: int = 30
    max_retries: int = 3


class LangfuseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIFLOW_LANGFUSE__")
    public_key: str | None = None
    secret_key: str | None = None
    host: str = "https://cloud.langfuse.com"
    enabled: bool = False
    cache_ttl: int = 300


class BudgetSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIFLOW_BUDGET__")
    default_per_run_usd: float = 10.0
    alert_threshold_pct: int = 80


class AIFlowSettings(BaseSettings):
    """Main configuration class. Reads AIFLOW_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="AIFLOW_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # App
    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    debug: bool = False
    log_level: str = "INFO"
    app_name: str = "aiflow"
    version: str = "0.1.0"

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    budget: BudgetSettings = Field(default_factory=BudgetSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> AIFlowSettings:
    """Singleton settings instance."""
    settings = AIFlowSettings()
    logger.info("settings_loaded", environment=settings.environment, debug=settings.debug)
    return settings
