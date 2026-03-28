"""
@test_registry:
    suite: skills-unit
    component: skills.loader
    covers: [src/aiflow/skills/loader.py]
    phase: 4
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [skills, loader, discovery, progressive-disclosure]
"""
from pathlib import Path

import pytest
import yaml

from aiflow.skills.loader import SkillLoader


def _write_skill_yaml(skill_dir: Path, name: str, **extra: object) -> Path:
    """Helper to create a skill.yaml in a subdirectory."""
    d = skill_dir / name
    d.mkdir(parents=True, exist_ok=True)
    data = {"name": name, **extra}
    f = d / "skill.yaml"
    f.write_text(yaml.dump(data), encoding="utf-8")
    return f


class TestSkillLoaderDiscover:
    def test_discover_finds_skills(self, tmp_path: Path):
        _write_skill_yaml(tmp_path, "skill-a", version="1.0.0")
        _write_skill_yaml(tmp_path, "skill-b", version="2.0.0")

        loader = SkillLoader()
        found = loader.discover(tmp_path)

        assert sorted(found) == ["skill-a", "skill-b"]
        assert loader.list_discovered() == found

    def test_discover_empty_directory(self, tmp_path: Path):
        loader = SkillLoader()
        found = loader.discover(tmp_path)
        assert found == []

    def test_discover_nonexistent_directory(self, tmp_path: Path):
        loader = SkillLoader()
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.discover(tmp_path / "nonexistent")

    def test_discover_skips_invalid_manifests(self, tmp_path: Path):
        _write_skill_yaml(tmp_path, "valid-skill")
        # Create an invalid skill.yaml
        bad_dir = tmp_path / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "skill.yaml").write_text("- not a mapping", encoding="utf-8")

        loader = SkillLoader()
        found = loader.discover(tmp_path)
        assert found == ["valid-skill"]


class TestSkillLoaderLoad:
    def test_load_single_skill(self, tmp_path: Path):
        path = _write_skill_yaml(tmp_path, "my-skill", version="1.0.0", description="A skill")

        loader = SkillLoader()
        manifest = loader.load(path)

        assert manifest.name == "my-skill"
        assert manifest.version == "1.0.0"
        assert loader.is_loaded("my-skill")
        assert loader.get_manifest("my-skill") is not None

    def test_load_missing_skill_yaml(self, tmp_path: Path):
        loader = SkillLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "missing" / "skill.yaml")

    def test_load_incompatible_framework(self, tmp_path: Path):
        path = _write_skill_yaml(
            tmp_path, "future-skill", framework_requires=">=99.0.0"
        )
        loader = SkillLoader()
        with pytest.raises(ValueError, match="incompatible"):
            loader.load(path)

    def test_get_path_returns_path(self, tmp_path: Path):
        path = _write_skill_yaml(tmp_path, "path-skill")
        loader = SkillLoader()
        loader.load(path)
        assert loader.get_path("path-skill") == path

    def test_get_manifest_unknown_returns_none(self):
        loader = SkillLoader()
        assert loader.get_manifest("unknown") is None
