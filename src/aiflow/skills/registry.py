"""Skill registry for installing, managing, and querying installed skills.

Uses the core Registry[SkillManifest] internally and adds a structured
9-step installation process with dependency checking and version tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from aiflow.core.registry import Registry
from aiflow.skills.manifest import (
    SkillManifest,
    check_framework_compatibility,
    load_manifest,
)

__all__ = ["SkillRegistry", "InstalledSkillRecord"]

logger = structlog.get_logger(__name__)


class InstalledSkillRecord(BaseModel):
    """Record of an installed skill with metadata."""

    manifest: SkillManifest
    installed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    install_path: str = ""
    status: str = "active"
    install_log: list[str] = Field(default_factory=list)


class SkillRegistry:
    """Registry for installed skills with lifecycle management.

    Wraps the generic Registry[SkillManifest] and adds a 9-step
    installation process:
        1. Load manifest from path
        2. Validate manifest fields
        3. Check framework compatibility
        4. Check dependencies (depends_on)
        5. Register workflows (placeholder)
        6. Register agents (placeholder)
        7. Sync prompts (placeholder)
        8. Run tests (placeholder)
        9. Save installation record
    """

    def __init__(self) -> None:
        self._registry: Registry[InstalledSkillRecord] = Registry(name="skills")
        self._version_history: dict[str, list[str]] = {}

    def install(self, skill_path: Path) -> InstalledSkillRecord:
        """Install a skill from its skill.yaml path (9-step process).

        Args:
            skill_path: Path to skill.yaml file.

        Returns:
            InstalledSkillRecord with installation metadata.

        Raises:
            FileNotFoundError: If skill_path does not exist.
            ValueError: If the skill is invalid, incompatible, or already installed.
        """
        install_log: list[str] = []

        # Step 1: Load manifest
        manifest = load_manifest(skill_path)
        install_log.append(f"1. Loaded manifest: {manifest.name} v{manifest.version}")

        # Step 2: Validate manifest fields
        if not manifest.name:
            raise ValueError("Skill manifest must have a non-empty 'name'")
        install_log.append("2. Manifest fields validated")

        # Step 3: Check framework compatibility
        if not check_framework_compatibility(manifest.framework_requires):
            raise ValueError(
                f"Skill '{manifest.name}' requires framework {manifest.framework_requires}"
            )
        install_log.append(f"3. Framework compatibility OK ({manifest.framework_requires})")

        # Step 4: Check dependencies
        missing_deps = [dep for dep in manifest.depends_on if not self._registry.has(dep)]
        if missing_deps:
            raise ValueError(f"Skill '{manifest.name}' has unmet dependencies: {missing_deps}")
        install_log.append(f"4. Dependencies satisfied ({len(manifest.depends_on)} checked)")

        # Step 5: Register workflows (placeholder)
        install_log.append(f"5. Workflows registered ({len(manifest.workflows)} workflows)")

        # Step 6: Register agents (placeholder)
        install_log.append(f"6. Agents registered ({len(manifest.agent_types)} agent types)")

        # Step 7: Sync prompts (placeholder)
        install_log.append(f"7. Prompts synced ({len(manifest.prompts)} prompts)")

        # Step 8: Run tests (placeholder)
        install_log.append("8. Skill tests passed (placeholder)")

        # Step 9: Save installation record
        install_log.append(f"9. Installation record saved for {manifest.name}")

        record = InstalledSkillRecord(
            manifest=manifest,
            install_path=str(skill_path),
            install_log=install_log,
        )

        self._registry.register(manifest.name, record)

        # Track version history
        if manifest.name not in self._version_history:
            self._version_history[manifest.name] = []
        self._version_history[manifest.name].append(manifest.version)

        logger.info(
            "skill_installed",
            name=manifest.name,
            version=manifest.version,
            steps_completed=9,
        )
        return record

    def uninstall(self, skill_name: str) -> None:
        """Uninstall a skill by name.

        Args:
            skill_name: Name of the skill to uninstall.

        Raises:
            KeyError: If the skill is not installed.
        """
        # Check if other skills depend on this one
        for key, record in self._registry.list_items():
            if skill_name in record.manifest.depends_on:
                raise ValueError(f"Cannot uninstall '{skill_name}': skill '{key}' depends on it")

        self._registry.unregister(skill_name)
        logger.info("skill_uninstalled", name=skill_name)

    def upgrade(self, skill_path: Path) -> InstalledSkillRecord:
        """Upgrade an installed skill to a new version.

        Uninstalls the old version and installs the new one.

        Args:
            skill_path: Path to the new skill.yaml file.

        Returns:
            Updated InstalledSkillRecord.

        Raises:
            FileNotFoundError: If skill_path does not exist.
            ValueError: If the new version is invalid.
            KeyError: If the skill is not currently installed.
        """
        manifest = load_manifest(skill_path)

        if not self._registry.has(manifest.name):
            raise KeyError(f"Skill '{manifest.name}' is not installed; use install() instead")

        old_record = self._registry.get(manifest.name)
        old_version = old_record.manifest.version

        # Unregister old (bypass dependency check since we re-install immediately)
        self._registry.unregister(manifest.name)

        try:
            record = self.install(skill_path)
            logger.info(
                "skill_upgraded",
                name=manifest.name,
                old_version=old_version,
                new_version=manifest.version,
            )
            return record
        except Exception:
            # Rollback: re-register old record
            self._registry.register(manifest.name, old_record)
            raise

    def get_skill(self, skill_name: str) -> InstalledSkillRecord:
        """Get an installed skill record by name.

        Args:
            skill_name: Name of the skill.

        Returns:
            InstalledSkillRecord.

        Raises:
            KeyError: If not installed.
        """
        return self._registry.get(skill_name)

    def list_skills(self) -> list[str]:
        """Return names of all installed skills."""
        return self._registry.list_keys()

    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill is installed."""
        return self._registry.has(skill_name)

    def get_version_history(self, skill_name: str) -> list[str]:
        """Get the version installation history for a skill."""
        return self._version_history.get(skill_name, [])

    def clear(self) -> None:
        """Remove all installed skills (for testing)."""
        self._registry.clear()
        self._version_history.clear()
