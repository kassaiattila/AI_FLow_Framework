"""YAML-to-Langfuse prompt synchronisation.

Syncs local YAML prompt definitions to Langfuse as the Cloud SSOT.
Actual Langfuse API integration is a placeholder for Phase 5.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from aiflow.prompts.schema import PromptDefinition

__all__ = ["PromptSyncer", "SyncResult", "DiffResult"]

logger = structlog.get_logger(__name__)


@dataclass
class SyncResult:
    """Result of a single prompt sync operation."""

    prompt_name: str
    label: str
    success: bool
    version: str = ""
    error: str = ""


@dataclass
class DiffResult:
    """Comparison between local YAML and remote Langfuse prompt."""

    prompt_name: str
    local_version: str
    remote_version: str | None
    has_changes: bool
    changed_fields: list[str] = field(default_factory=list)


class PromptSyncer:
    """Synchronises YAML prompt definitions to Langfuse.

    Provides sync_prompt, sync_directory, and diff operations.
    Actual Langfuse API calls are placeholders for Phase 5.

    Args:
        langfuse_client: Langfuse client instance (placeholder, can be None).
        dry_run: If True, simulate sync without making remote changes.
    """

    def __init__(
        self,
        langfuse_client: Any = None,
        dry_run: bool = False,
    ) -> None:
        self._client = langfuse_client
        self._dry_run = dry_run
        logger.info(
            "prompt_syncer.init",
            has_client=langfuse_client is not None,
            dry_run=dry_run,
        )

    def sync_prompt(self, yaml_path: Path | str, label: str = "dev") -> SyncResult:
        """Sync a single YAML prompt file to Langfuse.

        Args:
            yaml_path: Path to the YAML prompt file.
            label: Target environment label (dev/test/staging/prod).

        Returns:
            SyncResult indicating success or failure.
        """
        yaml_path = Path(yaml_path)

        try:
            prompt = self._load_prompt(yaml_path)
        except Exception as exc:
            return SyncResult(
                prompt_name=yaml_path.stem,
                label=label,
                success=False,
                error=str(exc),
            )

        if not prompt.langfuse.sync:
            logger.info(
                "prompt_syncer.skip_sync_disabled",
                prompt=prompt.name,
            )
            return SyncResult(
                prompt_name=prompt.name,
                label=label,
                success=True,
                version=prompt.version,
                error="sync disabled for this prompt",
            )

        # Phase 5: Actual Langfuse API call
        if not self._dry_run and self._client is not None:
            return self._push_to_langfuse(prompt, label)

        logger.info(
            "prompt_syncer.sync_prompt",
            prompt=prompt.name,
            label=label,
            version=prompt.version,
            dry_run=self._dry_run,
        )
        return SyncResult(
            prompt_name=prompt.name,
            label=label,
            success=True,
            version=prompt.version,
        )

    def sync_directory(
        self, dir_path: Path | str, label: str = "dev"
    ) -> list[SyncResult]:
        """Sync all YAML prompt files in a directory to Langfuse.

        Args:
            dir_path: Directory containing YAML prompt files.
            label: Target environment label.

        Returns:
            List of SyncResult for each file processed.
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        results: list[SyncResult] = []
        for ext in ("*.yaml", "*.yml"):
            for yaml_path in sorted(dir_path.glob(ext)):
                result = self.sync_prompt(yaml_path, label)
                results.append(result)

        logger.info(
            "prompt_syncer.sync_directory",
            directory=str(dir_path),
            total=len(results),
            success=sum(1 for r in results if r.success),
        )
        return results

    def diff(self, yaml_path: Path | str) -> DiffResult:
        """Compare local YAML prompt with remote Langfuse version.

        Args:
            yaml_path: Path to the local YAML prompt file.

        Returns:
            DiffResult describing differences.
        """
        yaml_path = Path(yaml_path)
        prompt = self._load_prompt(yaml_path)

        # Phase 5: Fetch remote and compare
        remote = self._fetch_remote(prompt.name)

        if remote is None:
            return DiffResult(
                prompt_name=prompt.name,
                local_version=prompt.version,
                remote_version=None,
                has_changes=True,
                changed_fields=["*new_prompt*"],
            )

        changed_fields = self._compute_diff(prompt, remote)
        return DiffResult(
            prompt_name=prompt.name,
            local_version=prompt.version,
            remote_version=remote.get("version", "unknown"),
            has_changes=len(changed_fields) > 0,
            changed_fields=changed_fields,
        )

    # --- Private helpers ---

    def _load_prompt(self, yaml_path: Path) -> PromptDefinition:
        """Load and parse a YAML prompt file."""
        if not yaml_path.exists():
            raise FileNotFoundError(f"Prompt YAML not found: {yaml_path}")

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML prompt format in {yaml_path}")

        return PromptDefinition(**data)

    def _fetch_remote(self, prompt_name: str) -> dict[str, Any] | None:
        """Fetch remote prompt from Langfuse (placeholder for Phase 5).

        Returns:
            Dict representation of the remote prompt, or None if not found.
        """
        logger.debug(
            "prompt_syncer.fetch_remote_placeholder",
            prompt=prompt_name,
            note="Langfuse integration in Phase 5",
        )
        return None

    def _push_to_langfuse(
        self, prompt: PromptDefinition, label: str
    ) -> SyncResult:
        """Push prompt to Langfuse API (placeholder for Phase 5).

        Returns:
            SyncResult from the push operation.
        """
        logger.debug(
            "prompt_syncer.push_placeholder",
            prompt=prompt.name,
            label=label,
        )
        return SyncResult(
            prompt_name=prompt.name,
            label=label,
            success=True,
            version=prompt.version,
        )

    def _compute_diff(
        self, local: PromptDefinition, remote: dict[str, Any]
    ) -> list[str]:
        """Compute list of changed field names between local and remote.

        Placeholder: will do deep comparison once Langfuse is integrated.
        """
        changed: list[str] = []
        local_dict = local.model_dump()

        for key, local_val in local_dict.items():
            remote_val = remote.get(key)
            if remote_val != local_val:
                changed.append(key)

        return changed
