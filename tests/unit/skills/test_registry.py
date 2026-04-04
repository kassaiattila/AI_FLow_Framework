"""
@test_registry:
    suite: skills-unit
    component: skills.registry
    covers: [src/aiflow/skills/registry.py]
    phase: 4
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [skills, registry, install, uninstall, lifecycle]
"""
from pathlib import Path

import pytest
import yaml

from aiflow.skills.registry import InstalledSkillRecord, SkillRegistry


def _write_skill(tmp_path: Path, name: str, **extra: object) -> Path:
    """Helper to create a skill.yaml file."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    data = {"name": name, **extra}
    f = d / "skill.yaml"
    f.write_text(yaml.dump(data), encoding="utf-8")
    return f


@pytest.fixture
def skill_registry() -> SkillRegistry:
    reg = SkillRegistry()
    yield reg
    reg.clear()


class TestSkillRegistryInstall:
    def test_install_skill(self, skill_registry: SkillRegistry, tmp_path: Path):
        path = _write_skill(tmp_path, "my-skill", version="1.0.0")
        record = skill_registry.install(path)

        assert isinstance(record, InstalledSkillRecord)
        assert record.manifest.name == "my-skill"
        assert record.manifest.version == "1.0.0"
        assert record.status == "active"
        assert len(record.install_log) >= 9

    def test_install_records_path(self, skill_registry: SkillRegistry, tmp_path: Path):
        path = _write_skill(tmp_path, "path-skill")
        record = skill_registry.install(path)
        assert str(path) in record.install_path

    def test_install_duplicate_raises(self, skill_registry: SkillRegistry, tmp_path: Path):
        path = _write_skill(tmp_path, "dup-skill")
        skill_registry.install(path)
        with pytest.raises(ValueError, match="already registered"):
            skill_registry.install(path)

    def test_install_with_missing_dependency_raises(
        self, skill_registry: SkillRegistry, tmp_path: Path
    ):
        path = _write_skill(tmp_path, "dep-skill", depends_on=["nonexistent-base"])
        with pytest.raises(ValueError, match="unmet dependencies"):
            skill_registry.install(path)

    def test_install_with_satisfied_dependency(
        self, skill_registry: SkillRegistry, tmp_path: Path
    ):
        base_path = _write_skill(tmp_path, "base-skill")
        skill_registry.install(base_path)

        child_path = _write_skill(tmp_path, "child-skill", depends_on=["base-skill"])
        record = skill_registry.install(child_path)
        assert record.manifest.name == "child-skill"


class TestSkillRegistryQuery:
    def test_get_skill(self, skill_registry: SkillRegistry, tmp_path: Path):
        path = _write_skill(tmp_path, "get-skill")
        skill_registry.install(path)
        record = skill_registry.get_skill("get-skill")
        assert record.manifest.name == "get-skill"

    def test_get_skill_missing_raises(self, skill_registry: SkillRegistry):
        with pytest.raises(KeyError, match="not found"):
            skill_registry.get_skill("missing-skill")

    def test_list_skills(self, skill_registry: SkillRegistry, tmp_path: Path):
        _write_skill(tmp_path, "skill-a")
        _write_skill(tmp_path, "skill-b")
        skill_registry.install(tmp_path / "skill-a" / "skill.yaml")
        skill_registry.install(tmp_path / "skill-b" / "skill.yaml")
        assert sorted(skill_registry.list_skills()) == ["skill-a", "skill-b"]

    def test_has_skill(self, skill_registry: SkillRegistry, tmp_path: Path):
        path = _write_skill(tmp_path, "exists-skill")
        assert skill_registry.has_skill("exists-skill") is False
        skill_registry.install(path)
        assert skill_registry.has_skill("exists-skill") is True


class TestSkillRegistryUninstall:
    def test_uninstall_skill(self, skill_registry: SkillRegistry, tmp_path: Path):
        path = _write_skill(tmp_path, "remove-me")
        skill_registry.install(path)
        skill_registry.uninstall("remove-me")
        assert skill_registry.has_skill("remove-me") is False

    def test_uninstall_missing_raises(self, skill_registry: SkillRegistry):
        with pytest.raises(KeyError):
            skill_registry.uninstall("ghost")

    def test_uninstall_with_dependents_raises(
        self, skill_registry: SkillRegistry, tmp_path: Path
    ):
        base_path = _write_skill(tmp_path, "base")
        skill_registry.install(base_path)
        child_path = _write_skill(tmp_path, "child", depends_on=["base"])
        skill_registry.install(child_path)

        with pytest.raises(ValueError, match="depends on it"):
            skill_registry.uninstall("base")


class TestSkillRegistryUpgrade:
    def test_upgrade_skill(self, skill_registry: SkillRegistry, tmp_path: Path):
        v1_path = _write_skill(tmp_path, "upgrade-skill", version="1.0.0")
        skill_registry.install(v1_path)

        # Create v2 in a different directory
        v2_dir = tmp_path / "v2"
        v2_path = _write_skill(v2_dir, "upgrade-skill", version="2.0.0")
        record = skill_registry.upgrade(v2_path)

        assert record.manifest.version == "2.0.0"
        assert skill_registry.get_skill("upgrade-skill").manifest.version == "2.0.0"

    def test_upgrade_not_installed_raises(
        self, skill_registry: SkillRegistry, tmp_path: Path
    ):
        path = _write_skill(tmp_path, "fresh-skill")
        with pytest.raises(KeyError, match="not installed"):
            skill_registry.upgrade(path)

    def test_version_history_tracked(self, skill_registry: SkillRegistry, tmp_path: Path):
        v1_path = _write_skill(tmp_path, "history-skill", version="1.0.0")
        skill_registry.install(v1_path)

        v2_dir = tmp_path / "v2"
        v2_path = _write_skill(v2_dir, "history-skill", version="2.0.0")
        skill_registry.upgrade(v2_path)

        history = skill_registry.get_version_history("history-skill")
        assert "1.0.0" in history
        assert "2.0.0" in history
