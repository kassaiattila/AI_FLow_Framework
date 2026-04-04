"""Skill discovery and loading with progressive disclosure.

The SkillLoader discovers skill.yaml manifests in a directory tree
and loads them on demand (metadata only until the skill is activated).
"""
from __future__ import annotations

from pathlib import Path

import structlog

from aiflow.skills.manifest import SkillManifest, check_framework_compatibility, load_manifest

__all__ = ["SkillLoader"]

logger = structlog.get_logger(__name__)


class SkillLoader:
    """Discovers and loads skill manifests with progressive disclosure.

    Only metadata (manifest) is loaded initially. Full skill activation
    (workflows, agents, prompts) happens when the skill is installed.
    """

    def __init__(self) -> None:
        self._discovered: dict[str, Path] = {}
        self._loaded: dict[str, SkillManifest] = {}

    def discover(self, skills_dir: Path) -> list[str]:
        """Discover all skill.yaml files in the given directory.

        Scans for skill.yaml files one level deep (skills_dir/*/skill.yaml).

        Args:
            skills_dir: Root directory containing skill packages.

        Returns:
            List of discovered skill names.

        Raises:
            FileNotFoundError: If skills_dir does not exist.
        """
        if not skills_dir.exists():
            raise FileNotFoundError(f"Skills directory not found: {skills_dir}")

        discovered: list[str] = []

        for manifest_path in sorted(skills_dir.glob("*/skill.yaml")):
            try:
                manifest = load_manifest(manifest_path)
                self._discovered[manifest.name] = manifest_path
                self._loaded[manifest.name] = manifest
                discovered.append(manifest.name)
            except (ValueError, FileNotFoundError) as exc:
                logger.warning(
                    "skill_discovery_skipped",
                    path=str(manifest_path),
                    error=str(exc),
                )

        logger.info("skills_discovered", count=len(discovered), directory=str(skills_dir))
        return discovered

    def load(self, skill_path: Path) -> SkillManifest:
        """Load a single skill manifest from a skill.yaml path.

        Args:
            skill_path: Path to skill.yaml file.

        Returns:
            Validated SkillManifest.

        Raises:
            FileNotFoundError: If skill_path does not exist.
            ValueError: If the manifest is invalid or incompatible.
        """
        manifest = load_manifest(skill_path)

        if not check_framework_compatibility(manifest.framework_requires):
            raise ValueError(
                f"Skill '{manifest.name}' requires framework {manifest.framework_requires}, "
                f"but current framework version is incompatible"
            )

        self._discovered[manifest.name] = skill_path
        self._loaded[manifest.name] = manifest
        return manifest

    def get_manifest(self, skill_name: str) -> SkillManifest | None:
        """Get a previously loaded manifest by name.

        Args:
            skill_name: Name of the skill.

        Returns:
            SkillManifest if loaded, else None.
        """
        return self._loaded.get(skill_name)

    def get_path(self, skill_name: str) -> Path | None:
        """Get the file path for a discovered skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Path to skill.yaml if discovered, else None.
        """
        return self._discovered.get(skill_name)

    def list_discovered(self) -> list[str]:
        """Return names of all discovered skills."""
        return list(self._discovered.keys())

    def is_loaded(self, skill_name: str) -> bool:
        """Check if a skill manifest has been loaded."""
        return skill_name in self._loaded
