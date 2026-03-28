"""Instance YAML loader and validator.

Loads instance config YAML files and validates them against the
InstanceConfig schema. Also loads deployment.yaml profiles
and resolves all instance references.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

import structlog

from aiflow.skills.instance import InstanceConfig

__all__ = [
    "load_instance_config",
    "load_deployment_profile",
    "DeploymentProfile",
    "CustomerInfo",
    "FrameworkInfo",
    "SkillTemplateRef",
    "InfrastructureConfig",
    "DatabaseConfig",
    "RedisConfig",
    "LangfuseConfig",
    "ResourceConfig",
]

logger = structlog.get_logger(__name__)


# --- Deployment profile models ---


class CustomerInfo(BaseModel):
    """Customer identification in deployment.yaml."""

    name: str
    display_name: str = ""
    contact_email: str = ""
    tier: str = "starter"


class FrameworkInfo(BaseModel):
    """Framework version and image variant."""

    version: str = "0.1.0"
    image_variant: str = "base"


class SkillTemplateRef(BaseModel):
    """Reference to a skill template with version."""

    name: str
    version: str = "0.1.0"


class DatabaseConfig(BaseModel):
    """Per-customer database configuration."""

    host: str = "localhost"
    name: str = "aiflow"
    schema_: str | None = Field(default=None, alias="schema")


class RedisConfig(BaseModel):
    """Per-customer Redis configuration."""

    db: int = 0
    prefix: str = ""


class LangfuseConfig(BaseModel):
    """Per-customer Langfuse project configuration."""

    project: str = ""
    prompt_label_prefix: str = ""


class ResourceConfig(BaseModel):
    """Container resource limits."""

    api_replicas: int = 1
    worker_replicas: int = 1
    rpa_worker_replicas: int = 0
    memory_limit: str = "2Gi"
    cpu_limit: str = "1000m"


class InfrastructureConfig(BaseModel):
    """Full infrastructure block in deployment.yaml."""

    docker_compose_project: str = ""
    k8s_namespace: str | None = None
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)


class InstanceRef(BaseModel):
    """Reference to an instance YAML file."""

    file: str


class DeploymentProfile(BaseModel):
    """Full customer deployment profile from deployment.yaml."""

    customer: CustomerInfo
    framework: FrameworkInfo = Field(default_factory=FrameworkInfo)
    skill_templates: list[SkillTemplateRef] = Field(default_factory=list)
    instances: list[InstanceRef] = Field(default_factory=list)
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)


# --- Loader functions ---


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read and parse a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}, got {type(data).__name__}")

    return data


def load_instance_config(path: Path) -> InstanceConfig:
    """Load and validate an instance config from a YAML file.

    Args:
        path: Path to the instance YAML file.

    Returns:
        Validated InstanceConfig.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If YAML is invalid or fails validation.
    """
    data = _read_yaml(path)

    try:
        config = InstanceConfig(**data)
    except Exception as exc:
        raise ValueError(f"Invalid instance config at {path}: {exc}") from exc

    logger.info(
        "instance_config_loaded",
        instance_name=config.instance_name,
        skill_template=config.skill_template,
        customer=config.customer,
    )
    return config


def load_deployment_profile(path: Path) -> DeploymentProfile:
    """Load a customer deployment profile from deployment.yaml.

    Args:
        path: Path to deployment.yaml.

    Returns:
        Validated DeploymentProfile.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If YAML is invalid or fails validation.
    """
    data = _read_yaml(path)

    try:
        profile = DeploymentProfile(**data)
    except Exception as exc:
        raise ValueError(f"Invalid deployment profile at {path}: {exc}") from exc

    logger.info(
        "deployment_profile_loaded",
        customer=profile.customer.name,
        tier=profile.customer.tier,
        skill_count=len(profile.skill_templates),
        instance_count=len(profile.instances),
    )
    return profile


def load_all_instances(deployment_path: Path) -> list[InstanceConfig]:
    """Load a deployment profile and all its referenced instance configs.

    Args:
        deployment_path: Path to deployment.yaml.

    Returns:
        List of validated InstanceConfig objects.

    Raises:
        FileNotFoundError: If deployment or instance files are missing.
        ValueError: If any config is invalid.
    """
    profile = load_deployment_profile(deployment_path)
    deployment_dir = deployment_path.parent

    instances: list[InstanceConfig] = []
    for ref in profile.instances:
        instance_path = deployment_dir / ref.file
        config = load_instance_config(instance_path)

        # Validate customer matches
        if config.customer != profile.customer.name:
            raise ValueError(
                f"Instance '{config.instance_name}' has customer='{config.customer}' "
                f"but deployment profile is for '{profile.customer.name}'"
            )

        instances.append(config)

    logger.info(
        "all_instances_loaded",
        customer=profile.customer.name,
        count=len(instances),
    )
    return instances
