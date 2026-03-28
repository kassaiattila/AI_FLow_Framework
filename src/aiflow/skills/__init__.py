"""AIFlow Skill System - backward compatibility re-exports.

DEPRECATED: Use aiflow.skill_system instead of aiflow.skills.
This module re-exports everything from aiflow.skill_system for backward compat.
"""
# Re-export from canonical location
from aiflow.skill_system import (  # noqa: F401
    SkillManifest,
    RequiredModel,
    VectorStoreConfig,
    SkillLoader,
    SkillRegistry,
    InstanceConfig,
    InstanceRegistry,
    DeploymentProfile,
    load_instance_config,
    load_deployment_profile,
)

__all__ = [
    "SkillManifest",
    "RequiredModel",
    "VectorStoreConfig",
    "SkillLoader",
    "SkillRegistry",
    "InstanceConfig",
    "InstanceRegistry",
    "DeploymentProfile",
    "load_instance_config",
    "load_deployment_profile",
]
