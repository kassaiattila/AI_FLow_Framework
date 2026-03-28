"""AIFlow Skill System - manifest parsing, discovery, loading, and registry.

Skills are self-contained packages of AI/RPA/hybrid capabilities
defined via skill.yaml manifests.
"""
from aiflow.skills.manifest import SkillManifest, RequiredModel, VectorStoreConfig
from aiflow.skills.loader import SkillLoader
from aiflow.skills.registry import SkillRegistry

__all__ = [
    "SkillManifest",
    "RequiredModel",
    "VectorStoreConfig",
    "SkillLoader",
    "SkillRegistry",
]
