"""AIFlow Skill System - manifest parsing, discovery, loading, and registry.

Skills are self-contained packages of AI/RPA/hybrid capabilities
defined via skill.yaml manifests. Instances are configured deployments
of skill templates per customer.
"""
from aiflow.skill_system.instance import InstanceConfig
from aiflow.skill_system.instance_loader import (
    DeploymentProfile,
    load_deployment_profile,
    load_instance_config,
)
from aiflow.skill_system.instance_registry import InstanceRegistry
from aiflow.skill_system.loader import SkillLoader
from aiflow.skill_system.manifest import RequiredModel, SkillManifest, VectorStoreConfig
from aiflow.skill_system.registry import SkillRegistry

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
