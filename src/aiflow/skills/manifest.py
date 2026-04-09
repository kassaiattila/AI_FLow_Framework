"""SkillManifest model parsed from skill.yaml files.

Each skill declares its metadata, dependencies, required models,
workflows, agent types, prompts, and estimated cost.
"""

from __future__ import annotations

from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field

from aiflow._version import __version__
from aiflow.core.types import SkillType

__all__ = [
    "SkillManifest",
    "RequiredModel",
    "VectorStoreConfig",
    "load_manifest",
    "check_framework_compatibility",
]

logger = structlog.get_logger(__name__)


class RequiredModel(BaseModel):
    """A model required by the skill."""

    name: str
    type: str = "llm"
    usage: str = ""
    optional: bool = False
    fallback: str | None = None


class VectorStoreConfig(BaseModel):
    """Vector store configuration for the skill."""

    collection_name: str = ""
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 512
    chunk_overlap: int = 50


class SkillManifest(BaseModel):
    """Full skill manifest matching the skill.yaml format."""

    name: str
    display_name: str = ""
    version: str = "0.1.0"
    skill_type: SkillType = SkillType.AI
    description: str = ""
    author: str = ""
    framework_requires: str = ">=0.1.0"
    capabilities: list[str] = Field(default_factory=list)
    required_models: list[RequiredModel] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    agent_types: list[str] = Field(default_factory=list)
    prompts: list[str] = Field(default_factory=list)
    estimated_cost_per_run: float = 0.0
    tags: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    vectorstore: VectorStoreConfig | None = None


def load_manifest(path: Path) -> SkillManifest:
    """Load and validate a SkillManifest from a YAML file.

    Args:
        path: Path to skill.yaml file.

    Returns:
        Validated SkillManifest instance.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the YAML is invalid or cannot be parsed.
    """
    if not path.exists():
        raise FileNotFoundError(f"Skill manifest not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Skill manifest must be a YAML mapping, got {type(data).__name__}")

    try:
        manifest = SkillManifest(**data)
    except Exception as exc:
        raise ValueError(f"Invalid skill manifest at {path}: {exc}") from exc

    logger.info(
        "skill_manifest_loaded",
        name=manifest.name,
        version=manifest.version,
        skill_type=manifest.skill_type,
    )
    return manifest


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a simple semver string into a tuple of ints."""
    parts = version_str.strip().split(".")
    result: list[int] = []
    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            break
    return tuple(result) if result else (0,)


def check_framework_compatibility(framework_requires: str) -> bool:
    """Check if the current framework version satisfies the requirement.

    Supports: >=X.Y.Z, <=X.Y.Z, ==X.Y.Z, >X.Y.Z, <X.Y.Z, and
    range expressions like >=X.Y.Z,<A.B.C

    Args:
        framework_requires: Version constraint string.

    Returns:
        True if the current framework version is compatible.
    """
    current = _parse_version(__version__)

    constraints = [c.strip() for c in framework_requires.split(",")]

    for constraint in constraints:
        if not constraint:
            continue

        if constraint.startswith(">="):
            required = _parse_version(constraint[2:])
            if current < required:
                return False
        elif constraint.startswith("<="):
            required = _parse_version(constraint[2:])
            if current > required:
                return False
        elif constraint.startswith("=="):
            required = _parse_version(constraint[2:])
            if current != required:
                return False
        elif constraint.startswith(">"):
            required = _parse_version(constraint[1:])
            if current <= required:
                return False
        elif constraint.startswith("<"):
            required = _parse_version(constraint[1:])
            if current >= required:
                return False
        else:
            # Treat as exact match
            required = _parse_version(constraint)
            if current != required:
                return False

    return True
