"""
@test_registry:
    suite: service-unit
    component: services.schema_registry
    covers: [src/aiflow/services/schema_registry/service.py]
    phase: B2.1
    priority: high
    estimated_duration_ms: 300
    requires_services: []
    tags: [service, schema-registry, filesystem]
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiflow.services.schema_registry.service import (
    SchemaRegistryConfig,
    SchemaRegistryService,
)


@pytest.fixture()
def schema_dir(tmp_path: Path) -> Path:
    """Create a temp skills dir with schema files."""
    skill_dir = tmp_path / "skills" / "test_skill" / "schemas" / "v1"
    skill_dir.mkdir(parents=True)
    (skill_dir / "input.json").write_text(
        json.dumps({"type": "object", "properties": {"text": {"type": "string"}}}),
        encoding="utf-8",
    )
    (skill_dir / "output.json").write_text(
        json.dumps({"type": "object", "properties": {"result": {"type": "string"}}}),
        encoding="utf-8",
    )
    return tmp_path / "skills"


@pytest.fixture()
def svc(schema_dir: Path) -> SchemaRegistryService:
    config = SchemaRegistryConfig(skills_dir=str(schema_dir))
    return SchemaRegistryService(config=config)


class TestSchemaRegistryService:
    def test_load_schema_existing(self, svc: SchemaRegistryService) -> None:
        """Load an existing schema returns parsed JSON dict."""
        schema = svc.load_schema("test_skill", "input")
        assert schema["type"] == "object"
        assert "text" in schema["properties"]

    def test_load_schema_not_found(self, svc: SchemaRegistryService) -> None:
        """Loading a non-existent skill raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            svc.load_schema("nonexistent_skill", "input")

    def test_list_versions(self, svc: SchemaRegistryService) -> None:
        """list_versions returns version directory names."""
        versions = svc.list_versions("test_skill")
        assert versions == ["v1"]

    def test_list_schema_types(self, svc: SchemaRegistryService) -> None:
        """list_schema_types returns schema file stems."""
        types = svc.list_schema_types("test_skill", "v1")
        assert sorted(types) == ["input", "output"]

    def test_invalidate_cache(self, svc: SchemaRegistryService) -> None:
        """invalidate_cache clears the internal cache."""
        # Populate cache
        svc.load_schema("test_skill", "input")
        assert len(svc._cache) > 0

        svc.invalidate_cache()
        assert len(svc._cache) == 0
