"""AIFlow configuration using pydantic-settings.

Loads from: environment variables (AIFLOW_ prefix) > aiflow.yaml > defaults.
"""

from functools import lru_cache
from typing import Literal

import structlog
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "AIFlowSettings",
    "CostGuardrailSettings",
    "UC3AttachmentIntentSettings",
    "UC3ExtractionSettings",
    "VaultSettings",
    "get_settings",
]

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


class CostGuardrailSettings(BaseSettings):
    """Pre-flight cost guardrail (Sprint N / S122).

    Gates projected LLM/pipeline cost against ``tenant_budgets`` before work
    starts. Flag-off by default; when ``enabled`` is flipped on the guardrail
    logs over-budget events but still allows the call until ``dry_run`` is
    turned off for enforced refusal.
    """

    model_config = SettingsConfigDict(env_prefix="AIFLOW_COST_GUARDRAIL__")
    enabled: bool = False
    dry_run: bool = True
    period: Literal["daily", "monthly"] = "daily"
    # Ceilings used when the caller cannot supply a per-call estimate.
    default_input_tokens: int = 4000
    default_output_tokens: int = 1000


class UC3AttachmentIntentSettings(BaseSettings):
    """UC3 attachment-aware intent feature flag (Sprint O / S127).

    When ``enabled`` is False (the default), the email-connector orchestrator
    runs the Sprint K body-only classification path with zero new behaviour —
    no ``AttachmentProcessor`` instantiation, no extractor calls, no new log
    events. Flip ``enabled`` to True per-tenant or globally to thread
    attachment features into ``workflow_runs.output_data`` for the classifier
    (S128 will consume them).
    """

    model_config = SettingsConfigDict(env_prefix="AIFLOW_UC3_ATTACHMENT_INTENT__")
    enabled: bool = False
    max_attachment_mb: int = 10
    total_budget_seconds: float = 5.0
    # S128 — when True (and ``enabled`` is also True) the classifier appends
    # an attachment-summary system message on the LLM path; default off so
    # rule-boost can land without paying the LLM-context budget yet.
    llm_context: bool = False
    # S132 — classifier strategy to use when flag-on. Sprint P measurement
    # showed SKLEARN_FIRST (keyword first, LLM fallback at < threshold)
    # drops misclass 32% → 12% on the 25-fixture corpus (body_only 3/6 → 6/6,
    # mixed 3/7 → 7/7). Operators can still set "sklearn_only" to preserve
    # the Sprint O latency/cost profile. Values: sklearn_only | sklearn_first
    # | llm_first | ensemble.
    classifier_strategy: str = "sklearn_first"


class UC3ExtractionSettings(BaseSettings):
    """UC3 extraction feature flag (Sprint Q / S135).

    Bridges Sprint P's intent classification with the ``invoice_processor``
    skill's extraction pipeline. When ``enabled`` is True and the UC3
    classifier outputs ``intent_class == "EXTRACT"`` on an email with
    PDF/DOCX attachments, the orchestrator runs the invoice extractor and
    merges the resulting structured fields into
    ``workflow_runs.output_data.extracted_fields``.

    Flag-off (default) restores Sprint P tip behaviour exactly — no import
    of the invoice_processor skill, no extra DB writes, no log events.
    """

    model_config = SettingsConfigDict(env_prefix="AIFLOW_UC3_EXTRACTION__")
    enabled: bool = False
    max_attachments_per_email: int = 5
    total_budget_seconds: float = 60.0
    # Per-invoice USD hard ceiling. The extractor runs two parallel LLM
    # calls (header + line items); pricing ~0.02 USD/invoice on
    # gpt-4o-mini. Ceiling leaves headroom for escalation to a larger
    # model (Sprint T).
    extraction_budget_usd: float = 0.05


class PromptWorkflowSettings(BaseSettings):
    """PromptWorkflow feature flag (Sprint R / S139).

    Gates the new ``PromptManager.get_workflow`` lookup path. When
    ``enabled`` is False (default) the manager raises
    ``FeatureDisabled("prompt_workflows")`` for any workflow request,
    keeping the codebase a pure no-op for callers until S140/S141 wire
    UI + skill consumers.
    """

    model_config = SettingsConfigDict(env_prefix="AIFLOW_PROMPT_WORKFLOWS__")
    enabled: bool = False
    workflows_dir: str = "prompts/workflows"
    cache_ttl_seconds: int = 300


class VaultSettings(BaseSettings):
    """HashiCorp Vault integration for production secret resolution.

    When ``enabled`` is ``False`` (the default) the :func:`build_secret_manager`
    factory returns an env-only :class:`SecretManager`, so local dev and CI
    behave exactly as before. Token auth is used in dev; AppRole
    (``role_id`` + ``secret_id``) is intended for prod.
    """

    model_config = SettingsConfigDict(env_prefix="AIFLOW_VAULT__")
    enabled: bool = False
    url: str = "http://localhost:8210"
    token: SecretStr | None = None
    role_id: str | None = None
    secret_id: SecretStr | None = None
    mount_point: str = "secret"
    kv_namespace: str = "aiflow"
    cache_ttl_seconds: float = 300.0
    negative_cache_ttl_seconds: float = 60.0


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
    cost_guardrail: CostGuardrailSettings = Field(default_factory=CostGuardrailSettings)
    uc3_attachment_intent: UC3AttachmentIntentSettings = Field(
        default_factory=UC3AttachmentIntentSettings
    )
    uc3_extraction: UC3ExtractionSettings = Field(default_factory=UC3ExtractionSettings)
    prompt_workflows: PromptWorkflowSettings = Field(default_factory=PromptWorkflowSettings)
    vault: VaultSettings = Field(default_factory=VaultSettings)

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
