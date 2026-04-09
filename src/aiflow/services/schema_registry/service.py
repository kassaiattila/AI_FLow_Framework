"""Schema registry service — centralized versioned JSON schema management.

Wraps the file-based SchemaRegistry as a BaseService with lifecycle management.
Supports customer-specific overrides and schema caching.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from aiflow.services.base import BaseService, ServiceConfig

__all__ = ["SchemaRegistryConfig", "SchemaRegistryService"]

logger = structlog.get_logger(__name__)


class SchemaRegistryConfig(ServiceConfig):
    """Schema registry service configuration."""

    skills_dir: str = "skills"
    customer: str | None = None
    deployments_dir: str | None = None


class SchemaRegistryService(BaseService):
    """Centralized schema registry as a managed service.

    Schema resolution order (first match wins):
    1. deployments/{customer}/schemas/{skill_name}/{schema_type}.json
    2. skills/{skill_name}/schemas/{version}/{schema_type}.json
    """

    def __init__(self, config: SchemaRegistryConfig | None = None) -> None:
        self._sr_config = config or SchemaRegistryConfig()
        super().__init__(self._sr_config)
        self._skills_dir = Path(self._sr_config.skills_dir)
        self._customer = self._sr_config.customer
        self._deployments_dir = (
            Path(self._sr_config.deployments_dir)
            if self._sr_config.deployments_dir
            else self._skills_dir.parent / "deployments"
        )
        self._cache: dict[str, dict] = {}

    @property
    def service_name(self) -> str:
        return "schema_registry"

    @property
    def service_description(self) -> str:
        return "Centralized versioned JSON schema management"

    async def _start(self) -> None:
        if not self._skills_dir.exists():
            self._logger.warning("skills_dir_missing", path=str(self._skills_dir))

    async def _stop(self) -> None:
        self._cache.clear()

    async def health_check(self) -> bool:
        return self._skills_dir.exists()

    def load_schema(
        self, skill_name: str, schema_type: str, version: str = "latest"
    ) -> dict[str, Any]:
        """Load a schema JSON file."""
        cache_key = f"{self._customer or ''}:{skill_name}:{schema_type}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._customer:
            customer_path = (
                self._deployments_dir
                / self._customer
                / "schemas"
                / skill_name
                / f"{schema_type}.json"
            )
            if customer_path.exists():
                data = json.loads(customer_path.read_text(encoding="utf-8"))
                self._cache[cache_key] = data
                self._logger.info(
                    "schema_loaded",
                    skill=skill_name,
                    type=schema_type,
                    source=f"customer:{self._customer}",
                )
                return data

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
        self._logger.info("schema_loaded", skill=skill_name, type=schema_type, version=version)
        return data

    def list_versions(self, skill_name: str) -> list[str]:
        """List available schema versions for a skill."""
        schema_dir = self._skills_dir / skill_name / "schemas"
        if not schema_dir.exists():
            return []
        return sorted(d.name for d in schema_dir.iterdir() if d.is_dir() and d.name.startswith("v"))

    def list_schema_types(self, skill_name: str, version: str = "latest") -> list[str]:
        """List available schema types for a version."""
        schema_dir = self._skills_dir / skill_name / "schemas"
        if version == "latest":
            version = self._find_latest_version(schema_dir)
        ver_dir = schema_dir / version
        if not ver_dir.exists():
            return []
        return sorted(f.stem for f in ver_dir.glob("*.json"))

    def get_items(self, skill_name: str, schema_type: str, version: str = "latest") -> list[dict]:
        """Get the main items list from a schema."""
        schema = self.load_schema(skill_name, schema_type, version)
        for key in [
            schema_type,
            f"{schema_type[:-1]}_types" if schema_type.endswith("s") else schema_type,
            "items",
            "definitions",
        ]:
            if key in schema and isinstance(schema[key], list):
                return schema[key]
        return []

    def invalidate_cache(self) -> None:
        """Clear all cached schemas."""
        self._cache.clear()

    def _find_latest_version(self, schema_dir: Path) -> str:
        versions = sorted(
            d.name for d in schema_dir.iterdir() if d.is_dir() and d.name.startswith("v")
        )
        if not versions:
            raise FileNotFoundError(f"No versions in {schema_dir}")
        return versions[-1]
