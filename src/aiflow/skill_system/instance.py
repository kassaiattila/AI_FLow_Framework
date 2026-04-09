"""Skill Instance models - configured deployments of skill templates.

A Skill is a template (code). An Instance is a running configuration
of that template for a specific customer with its own data sources,
prompts, models, budget, and SLA targets.

Schema follows 28_MODULAR_DEPLOYMENT.md Section 2.1.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "InstanceConfig",
    "DataSourceConfig",
    "CollectionRef",
    "PromptConfig",
    "PromptOverride",
    "ModelConfig",
    "BudgetConfig",
    "SLAConfig",
    "IntentConfig",
    "RoutingConfig",
]


class CollectionRef(BaseModel):
    """Reference to a vector collection with search priority."""

    name: str
    priority: int = 1


class DataSourceConfig(BaseModel):
    """Data source configuration for RAG skills."""

    collections: list[CollectionRef] = Field(default_factory=list)
    document_filters: dict[str, Any] = Field(default_factory=dict)
    embedding_model: str | None = "text-embedding-3-small"


class PromptOverride(BaseModel):
    """Override for a specific prompt within the instance."""

    prompt_name: str
    template: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)


class PromptConfig(BaseModel):
    """Prompt configuration for an instance (Langfuse namespace isolation)."""

    namespace: str
    label: str = "prod"
    overrides: list[PromptOverride] = Field(default_factory=list)


class ModelConfig(BaseModel):
    """LLM model selection per instance."""

    default: str = "gpt-4o"
    fallback: str | None = "gpt-4o-mini"
    per_agent: dict[str, str] = Field(default_factory=dict)


class BudgetConfig(BaseModel):
    """Cost budget limits per instance."""

    monthly_usd: float = 100.0
    per_run_usd: float = 0.50
    alert_threshold: float = 0.8


class SLAConfig(BaseModel):
    """Service-level targets per instance."""

    target_seconds: int = 10
    p95_target_seconds: int = 20
    availability: float = 0.99


class IntentConfig(BaseModel):
    """Intent definition for email/intent-based skills."""

    name: str
    description: str = ""
    handler: str = ""
    priority: int = 1
    auto_respond: bool = False


class RoutingConfig(BaseModel):
    """I/O routing configuration."""

    input_channel: str = "api"
    output_channel: str = "api"
    webhook_url: str | None = None
    queue_name: str | None = None


class InstanceConfig(BaseModel):
    """Full instance configuration parsed from YAML.

    Maps to deployments/{customer}/instances/{instance_name}.yaml
    """

    instance_name: str
    display_name: str = ""
    skill_template: str
    version: str = "0.1.0"
    customer: str
    enabled: bool = True

    data_sources: DataSourceConfig = Field(default_factory=DataSourceConfig)
    prompts: PromptConfig
    models: ModelConfig = Field(default_factory=ModelConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    sla: SLAConfig = Field(default_factory=SLAConfig)
    intents: list[IntentConfig] = Field(default_factory=list)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
