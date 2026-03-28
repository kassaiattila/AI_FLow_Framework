"""AIFlow Skill System - manifest parsing, discovery, loading, and registry.

Skills are self-contained packages of AI/RPA/hybrid capabilities
defined via skill.yaml manifests. Instances are configured deployments
of skill templates per customer.
"""
from aiflow.skill_system.manifest import SkillManifest, RequiredModel, VectorStoreConfig
from aiflow.skill_system.loader import SkillLoader
from aiflow.skill_system.registry import SkillRegistry
from aiflow.skill_system.instance import InstanceConfig
from aiflow.skill_system.instance_loader import load_instance_config, load_deployment_profile, DeploymentProfile
from aiflow.skill_system.instance_registry import InstanceRegistry

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
