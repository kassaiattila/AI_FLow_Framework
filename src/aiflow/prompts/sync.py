"""YAML-to-Langfuse prompt synchronisation.

Syncs local YAML prompt definitions to Langfuse as the Cloud SSOT.
Uses Langfuse v4 SDK: create_prompt (chat type) and get_prompt.
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
    Uses Langfuse v4 SDK for real cloud synchronisation.

    Args:
        langfuse_client: Langfuse client instance (from get_langfuse_client() or direct).
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

    def diff(self, yaml_path: Path | str, label: str = "prod") -> DiffResult:
        """Compare local YAML prompt with remote Langfuse version.

        Args:
            yaml_path: Path to the local YAML prompt file.
            label: Langfuse label to compare against.

        Returns:
            DiffResult describing differences.
        """
        yaml_path = Path(yaml_path)
        prompt = self._load_prompt(yaml_path)

        remote = self._fetch_remote(prompt.name, label=label)

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

    def _fetch_remote(self, prompt_name: str, label: str = "prod") -> dict[str, Any] | None:
        """Fetch remote prompt from Langfuse.

        Uses Langfuse v4 get_prompt() API. Returns a dict with prompt fields
        or None if the prompt doesn't exist remotely.
        """
        if not self._client:
            logger.debug("prompt_syncer.fetch_remote_no_client", prompt=prompt_name)
            return None

        try:
            remote = self._client.get_prompt(name=prompt_name, label=label, type="chat")
            # ChatPromptClient: name, version, config, labels, prompt are direct attributes
            result: dict[str, Any] = {
                "name": remote.name,
                "version": str(remote.version),
                "config": remote.config or {},
                "labels": list(remote.labels) if remote.labels else [],
                "prompt": remote.prompt,  # the message list
            }
            logger.info("prompt_syncer.fetch_remote_ok", prompt=prompt_name, version=result["version"])
            return result
        except Exception as exc:
            error_str = str(exc)
            if "not found" in error_str.lower() or "404" in error_str:
                logger.debug("prompt_syncer.fetch_remote_not_found", prompt=prompt_name)
                return None
            logger.warning("prompt_syncer.fetch_remote_failed", prompt=prompt_name, error=error_str)
            return None

    def _push_to_langfuse(
        self, prompt: PromptDefinition, label: str
    ) -> SyncResult:
        """Push prompt to Langfuse using v4 create_prompt() API.

        Creates a new version of the prompt in Langfuse as a chat prompt
        (system + user messages). Config and metadata are stored in the
        prompt's config field.
        """
        if not self._client:
            return SyncResult(
                prompt_name=prompt.name,
                label=label,
                success=False,
                error="No Langfuse client available",
            )

        try:
            # Build chat messages from YAML system/user templates
            messages: list[dict[str, str]] = []
            if prompt.system:
                messages.append({"role": "system", "content": prompt.system})
            if prompt.user:
                messages.append({"role": "user", "content": prompt.user})

            # Config to store alongside the prompt
            config = {
                "model": prompt.config.model,
                "temperature": prompt.config.temperature,
                "max_tokens": prompt.config.max_tokens,
                "yaml_version": prompt.version,
                "description": prompt.description,
            }
            if prompt.config.response_format:
                config["response_format"] = prompt.config.response_format

            # Push to Langfuse
            result = self._client.create_prompt(
                name=prompt.name,
                prompt=messages,
                type="chat",
                labels=[label],
                tags=prompt.metadata.tags if prompt.metadata.tags else None,
                config=config,
                commit_message=f"Synced from YAML v{prompt.version} (label={label})",
            )

            # ChatPromptClient: version is a direct attribute
            remote_version = str(result.version) if hasattr(result, "version") else prompt.version

            logger.info(
                "prompt_syncer.push_ok",
                prompt=prompt.name,
                label=label,
                version=remote_version,
            )
            return SyncResult(
                prompt_name=prompt.name,
                label=label,
                success=True,
                version=remote_version,
            )
        except Exception as exc:
            logger.warning(
                "prompt_syncer.push_failed",
                prompt=prompt.name,
                label=label,
                error=str(exc),
            )
            return SyncResult(
                prompt_name=prompt.name,
                label=label,
                success=False,
                error=str(exc),
            )

    def _compute_diff(
        self, local: PromptDefinition, remote: dict[str, Any]
    ) -> list[str]:
        """Compute list of changed field names between local and remote."""
        changed: list[str] = []

        # Compare system/user content against remote messages
        remote_messages = remote.get("prompt", [])
        remote_system = ""
        remote_user = ""
        if isinstance(remote_messages, list):
            for msg in remote_messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        remote_system = msg.get("content", "")
                    elif msg.get("role") == "user":
                        remote_user = msg.get("content", "")

        if local.system.strip() != remote_system.strip():
            changed.append("system")
        if local.user.strip() != remote_user.strip():
            changed.append("user")

        # Compare config
        remote_config = remote.get("config", {})
        if remote_config.get("model") != local.config.model:
            changed.append("config.model")
        if remote_config.get("temperature") != local.config.temperature:
            changed.append("config.temperature")
        if remote_config.get("max_tokens") != local.config.max_tokens:
            changed.append("config.max_tokens")
        if remote_config.get("yaml_version") != local.version:
            changed.append("version")

        return changed
