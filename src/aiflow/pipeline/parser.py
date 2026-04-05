"""Pipeline YAML parser — load and validate pipeline definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from aiflow.pipeline.schema import PipelineDefinition

__all__ = ["PipelineParser", "PipelineParseError"]

logger = structlog.get_logger(__name__)


class PipelineParseError(Exception):
    """Raised when pipeline YAML parsing or validation fails."""


class PipelineParser:
    """Parse pipeline YAML into validated PipelineDefinition models."""

    def parse_yaml(self, yaml_content: str) -> PipelineDefinition:
        """Parse YAML string into PipelineDefinition.

        Raises PipelineParseError on YAML syntax or validation errors.
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as exc:
            raise PipelineParseError(f"Invalid YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise PipelineParseError(
                f"Pipeline YAML must be a mapping, got {type(data).__name__}"
            )

        return self._validate(data)

    def parse_file(self, file_path: str | Path) -> PipelineDefinition:
        """Parse pipeline YAML from a file path.

        Raises PipelineParseError if file not found or invalid.
        """
        path = Path(file_path)
        if not path.exists():
            raise PipelineParseError(f"Pipeline file not found: {path}")
        if path.suffix not in (".yaml", ".yml"):
            raise PipelineParseError(
                f"Expected .yaml/.yml file, got: {path.suffix}"
            )

        content = path.read_text(encoding="utf-8")
        logger.info("pipeline_file_loaded", path=str(path), size=len(content))
        return self.parse_yaml(content)

    def parse_dict(self, data: dict[str, Any]) -> PipelineDefinition:
        """Parse pipeline from a dict (e.g. from API request body)."""
        return self._validate(data)

    def _validate(self, data: dict[str, Any]) -> PipelineDefinition:
        """Validate raw dict into PipelineDefinition.

        Performs structural + cross-reference validation.
        """
        try:
            pipeline = PipelineDefinition.model_validate(data)
        except Exception as exc:
            raise PipelineParseError(
                f"Pipeline validation failed: {exc}"
            ) from exc

        errors = self._cross_validate(pipeline)
        if errors:
            raise PipelineParseError(
                f"Pipeline cross-validation failed: {'; '.join(errors)}"
            )

        logger.info(
            "pipeline_parsed",
            name=pipeline.name,
            steps=len(pipeline.steps),
        )
        return pipeline

    @staticmethod
    def _cross_validate(pipeline: PipelineDefinition) -> list[str]:
        """Cross-reference validation: depends_on references, etc."""
        errors: list[str] = []
        step_names = set(pipeline.step_names())

        for step in pipeline.steps:
            for dep in step.depends_on:
                if dep not in step_names:
                    errors.append(
                        f"Step '{step.name}' depends on unknown step '{dep}'"
                    )
                if dep == step.name:
                    errors.append(
                        f"Step '{step.name}' cannot depend on itself"
                    )

        return errors
