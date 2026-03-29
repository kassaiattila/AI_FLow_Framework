"""Schema registry - load and validate versioned JSON schema definitions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

__all__ = ["SchemaRegistry"]
logger = structlog.get_logger(__name__)


class SchemaRegistry:
    """Load versioned JSON schemas from skill directories.

    Schemas live in: skills/{skill_name}/schemas/{version}/{schema_type}.json
    """

    def __init__(self, skills_dir: Path | str = "skills"):
        self._skills_dir = Path(skills_dir)
        self._cache: dict[str, dict] = {}

    def load_schema(
        self, skill_name: str, schema_type: str, version: str = "latest"
    ) -> dict[str, Any]:
        """Load a schema JSON file.

        Args:
            skill_name: e.g. "email_intent_processor"
            schema_type: e.g. "intents", "entities", "document_types"
            version: e.g. "v1", or "latest" for highest version
        """
        cache_key = f"{skill_name}:{schema_type}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        schema_dir = self._skills_dir / skill_name / "schemas"
        if not schema_dir.exists():
            raise FileNotFoundError(f"No schemas directory: {schema_dir}")

        if version == "latest":
            version = self._find_latest_version(schema_dir)

        path = schema_dir / version / f"{schema_type}.json"
        if not path.exists():
            raise FileNotFoundError(f"Schema not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        self._cache[cache_key] = data
        logger.info(
            "schema_loaded", skill=skill_name, type=schema_type, version=version
        )
        return data

    def list_versions(self, skill_name: str) -> list[str]:
        """List available schema versions for a skill."""
        schema_dir = self._skills_dir / skill_name / "schemas"
        if not schema_dir.exists():
            return []
        return sorted(
            [d.name for d in schema_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        )

    def list_schema_types(
        self, skill_name: str, version: str = "latest"
    ) -> list[str]:
        """List available schema types for a version."""
        schema_dir = self._skills_dir / skill_name / "schemas"
        if version == "latest":
            version = self._find_latest_version(schema_dir)
        ver_dir = schema_dir / version
        if not ver_dir.exists():
            return []
        return sorted([f.stem for f in ver_dir.glob("*.json")])

    def get_items(
        self, skill_name: str, schema_type: str, version: str = "latest"
    ) -> list[dict]:
        """Get the main items list from a schema (e.g., intents, entity_types)."""
        schema = self.load_schema(skill_name, schema_type, version)
        # Try common list field names
        for key in [
            schema_type,
            f"{schema_type[:-1]}_types" if schema_type.endswith("s") else schema_type,
            "items",
            "definitions",
        ]:
            if key in schema and isinstance(schema[key], list):
                return schema[key]
        return []

    def _find_latest_version(self, schema_dir: Path) -> str:
        versions = sorted(
            [
                d.name
                for d in schema_dir.iterdir()
                if d.is_dir() and d.name.startswith("v")
            ]
        )
        if not versions:
            raise FileNotFoundError(f"No versions in {schema_dir}")
        return versions[-1]

    def invalidate_cache(self) -> None:
        """Clear all cached schemas."""
        self._cache.clear()
