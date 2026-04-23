"""Unit tests for aiflow.tools.schema_registry — coverage uplift (issue #7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiflow.tools.schema_registry import SchemaRegistry


def _make_skill_schemas(
    skills_dir: Path, skill: str, version: str, schemas: dict[str, dict]
) -> None:
    """Create skills/<skill>/schemas/<version>/<type>.json files."""
    target = skills_dir / skill / "schemas" / version
    target.mkdir(parents=True, exist_ok=True)
    for schema_type, payload in schemas.items():
        (target / f"{schema_type}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_load_schema_default(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"intents": [{"id": "greet"}]}})
    reg = SchemaRegistry(skills_dir=skills)

    data = reg.load_schema("demo", "intents", "v1")
    assert data == {"intents": [{"id": "greet"}]}


def test_load_schema_latest_version_picks_highest(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"intents": ["a"]}})
    _make_skill_schemas(skills, "demo", "v3", {"intents": {"intents": ["c"]}})
    _make_skill_schemas(skills, "demo", "v2", {"intents": {"intents": ["b"]}})
    reg = SchemaRegistry(skills_dir=skills)

    data = reg.load_schema("demo", "intents")  # latest
    assert data == {"intents": ["c"]}


def test_load_schema_caches(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"intents": []}})
    reg = SchemaRegistry(skills_dir=skills)

    reg.load_schema("demo", "intents", "v1")
    # Overwrite underlying file; cache should win
    (skills / "demo" / "schemas" / "v1" / "intents.json").write_text(
        json.dumps({"intents": ["changed"]}), encoding="utf-8"
    )
    data2 = reg.load_schema("demo", "intents", "v1")
    assert data2 == {"intents": []}

    reg.invalidate_cache()
    data3 = reg.load_schema("demo", "intents", "v1")
    assert data3 == {"intents": ["changed"]}


def test_load_schema_customer_override_wins(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"intents": ["default"]}})

    deployments = tmp_path / "deployments"
    cust_path = deployments / "acme" / "schemas" / "demo"
    cust_path.mkdir(parents=True)
    (cust_path / "intents.json").write_text(json.dumps({"intents": ["acme"]}), encoding="utf-8")

    reg = SchemaRegistry(skills_dir=skills, customer="acme", deployments_dir=deployments)
    data = reg.load_schema("demo", "intents")
    assert data == {"intents": ["acme"]}


def test_load_schema_missing_dir_raises(tmp_path: Path) -> None:
    reg = SchemaRegistry(skills_dir=tmp_path / "empty")
    with pytest.raises(FileNotFoundError):
        reg.load_schema("missing", "intents")


def test_load_schema_missing_file_raises(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"intents": []}})
    reg = SchemaRegistry(skills_dir=skills)
    with pytest.raises(FileNotFoundError):
        reg.load_schema("demo", "entities", "v1")


def test_list_versions(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {}})
    _make_skill_schemas(skills, "demo", "v2", {"intents": {}})
    reg = SchemaRegistry(skills_dir=skills)
    assert reg.list_versions("demo") == ["v1", "v2"]
    assert reg.list_versions("nonexistent") == []


def test_list_schema_types(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(
        skills,
        "demo",
        "v1",
        {"intents": {}, "entities": {}, "document_types": {}},
    )
    reg = SchemaRegistry(skills_dir=skills)
    assert reg.list_schema_types("demo", "v1") == [
        "document_types",
        "entities",
        "intents",
    ]
    assert reg.list_schema_types("demo", "v2") == []  # missing version → empty


def test_get_items_direct_key(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"intents": [{"id": "a"}, {"id": "b"}]}})
    reg = SchemaRegistry(skills_dir=skills)
    items = reg.get_items("demo", "intents", "v1")
    assert items == [{"id": "a"}, {"id": "b"}]


def test_get_items_plural_key(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    # schema_type "intents" with body keyed "items"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"items": [{"id": "x"}]}})
    reg = SchemaRegistry(skills_dir=skills)
    assert reg.get_items("demo", "intents", "v1") == [{"id": "x"}]


def test_get_items_empty_when_no_list_present(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill_schemas(skills, "demo", "v1", {"intents": {"unrelated": "scalar"}})
    reg = SchemaRegistry(skills_dir=skills)
    assert reg.get_items("demo", "intents", "v1") == []


def test_find_latest_version_no_versions(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    (skills / "demo" / "schemas").mkdir(parents=True)
    reg = SchemaRegistry(skills_dir=skills)
    with pytest.raises(FileNotFoundError):
        reg.load_schema("demo", "intents")
