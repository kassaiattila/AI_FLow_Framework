"""Pipeline template registry — discovers and serves built-in YAML templates."""

from __future__ import annotations

from pathlib import Path

import structlog
from pydantic import BaseModel, Field

__all__ = ["TemplateInfo", "TemplateRegistry"]

logger = structlog.get_logger(__name__)

# Default template directory relative to this file
_DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "builtin_templates"


class TemplateInfo(BaseModel):
    """Metadata about a pipeline template."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    step_count: int = 0
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    file_name: str = ""


class TemplateRegistry:
    """Discovers and serves built-in pipeline YAML templates.

    Scans a directory for ``*.yaml`` files, parses basic metadata from
    each, and provides lookup by name.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        self._dir = template_dir or _DEFAULT_TEMPLATE_DIR
        self._templates: dict[str, TemplateInfo] = {}
        self._yaml_cache: dict[str, str] = {}

    def discover(self) -> list[TemplateInfo]:
        """Scan the template directory for YAML files and index them.

        Returns the list of discovered templates.
        """
        self._templates.clear()
        self._yaml_cache.clear()

        if not self._dir.exists():
            logger.warning(
                "template_dir_not_found", path=str(self._dir)
            )
            return []

        discovered: list[TemplateInfo] = []
        for yaml_path in sorted(self._dir.glob("*.yaml")):
            try:
                info = self._parse_template_file(yaml_path)
                self._templates[info.name] = info
                self._yaml_cache[info.name] = yaml_path.read_text(
                    encoding="utf-8"
                )
                discovered.append(info)
            except Exception:
                logger.warning(
                    "template_parse_failed",
                    file=yaml_path.name,
                    exc_info=True,
                )

        logger.info(
            "templates_discovered",
            count=len(discovered),
            names=[t.name for t in discovered],
        )
        return discovered

    def get(self, name: str) -> TemplateInfo | None:
        """Get template metadata by name."""
        if not self._templates:
            self.discover()
        return self._templates.get(name)

    def get_yaml(self, name: str) -> str | None:
        """Get raw YAML content by template name."""
        if not self._yaml_cache:
            self.discover()
        return self._yaml_cache.get(name)

    def list_all(self) -> list[TemplateInfo]:
        """Return all discovered templates."""
        if not self._templates:
            self.discover()
        return list(self._templates.values())

    def _parse_template_file(self, path: Path) -> TemplateInfo:
        """Parse a YAML template file and extract metadata.

        Uses a lightweight line-based parser to avoid requiring PyYAML
        as a hard dependency at import time (though it is available).
        """
        import yaml

        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise ValueError(
                f"Template {path.name} does not contain a YAML mapping"
            )

        name = data.get("name", path.stem)
        version = str(data.get("version", "1.0.0"))
        description = data.get("description", "")
        steps = data.get("steps", [])
        metadata = data.get("metadata", {})

        category = metadata.get("category", "")
        tier = metadata.get("tier", "")
        cycle = metadata.get("cycle", "")

        tags: list[str] = []
        if category:
            tags.append(category)
        if tier:
            tags.append(f"tier-{tier}")
        if cycle:
            tags.append(cycle)

        return TemplateInfo(
            name=name,
            version=version,
            description=description,
            step_count=len(steps),
            tags=tags,
            category=category,
            file_name=path.name,
        )
