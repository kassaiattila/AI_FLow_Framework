"""Filesystem YAML loader for :class:`PromptWorkflow` descriptors.

Mirrors :class:`aiflow.prompts.manager.PromptManager.load_yaml` for the
workflow domain. Does NOT resolve nested prompts — the manager's
``get_workflow`` does that.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from aiflow.prompts.workflow import PromptWorkflow, WorkflowValidationError

__all__ = ["PromptWorkflowLoader", "WorkflowYamlError"]

logger = structlog.get_logger(__name__)


class WorkflowYamlError(ValueError):
    """Raised when a workflow YAML file is malformed or fails validation."""


class PromptWorkflowLoader:
    """Discovers + parses ``*.yaml`` workflow descriptors under a directory."""

    def __init__(self, workflows_dir: Path | str) -> None:
        self._dir = Path(workflows_dir)
        self._registry: dict[str, Path] = {}

    def load_from_yaml(self, path: Path | str) -> PromptWorkflow:
        """Parse a single YAML file into a :class:`PromptWorkflow`.

        Raises :class:`WorkflowYamlError` with the offending path on any
        parse / validation failure.
        """
        path = Path(path)
        if not path.exists():
            raise WorkflowYamlError(f"workflow YAML not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data: Any = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise WorkflowYamlError(f"invalid YAML in {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise WorkflowYamlError(f"workflow YAML must be a mapping at top level: {path}")

        try:
            wf = PromptWorkflow(**data)
        except WorkflowValidationError as exc:
            raise WorkflowYamlError(f"workflow validation failed in {path}: {exc}") from exc
        except Exception as exc:
            raise WorkflowYamlError(f"workflow parse failed in {path}: {exc}") from exc

        logger.debug("workflow_loader.load_from_yaml", path=str(path), name=wf.name)
        return wf

    def register_dir(self) -> int:
        """Discover all ``*.yaml`` workflows in the configured directory.

        Returns the number of workflows successfully registered. Files
        that fail validation are logged + skipped (not raised) — same
        defensive policy as :meth:`PromptManager.register_yaml_dir`.
        """
        if not self._dir.is_dir():
            logger.info("workflow_loader.dir_missing", directory=str(self._dir))
            return 0

        count = 0
        for yaml_path in sorted(self._dir.glob("*.yaml")):
            try:
                wf = self.load_from_yaml(yaml_path)
                self._registry[wf.name] = yaml_path
                count += 1
            except WorkflowYamlError as exc:
                logger.warning(
                    "workflow_loader.register_skip",
                    path=str(yaml_path),
                    error=str(exc),
                )

        logger.info(
            "workflow_loader.register_dir",
            directory=str(self._dir),
            count=count,
        )
        return count

    def list_local(self) -> list[str]:
        """Return the names of all workflows registered from the local dir."""
        return list(self._registry.keys())

    def path_for(self, name: str) -> Path | None:
        """Return the YAML path backing ``name`` if registered, else ``None``."""
        return self._registry.get(name)
