"""
@test_registry:
    suite: skills-unit
    component: skills.manifest
    covers: [src/aiflow/skills/manifest.py]
    phase: 4
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [skills, manifest, yaml, parsing, validation]
"""
from pathlib import Path

import pytest
import yaml

from aiflow.core.types import SkillType
from aiflow.skills.manifest import (
    RequiredModel,
    SkillManifest,
    VectorStoreConfig,
    _parse_version,
    check_framework_compatibility,
    load_manifest,
)


@pytest.fixture
def full_manifest_yaml(tmp_path: Path) -> Path:
    """Create a complete skill.yaml for testing."""
    data = {
        "name": "invoice-classifier",
        "display_name": "Invoice Classifier",
        "version": "1.2.0",
        "skill_type": "ai",
        "description": "Classifies incoming invoices by type and urgency",
        "author": "BestIxCom Kft",
        "framework_requires": ">=0.1.0",
        "capabilities": ["classification", "extraction"],
        "required_models": [
            {
                "name": "gpt-4o",
                "type": "llm",
                "usage": "primary classification",
                "optional": False,
                "fallback": "gpt-4o-mini",
            },
            {
                "name": "text-embedding-3-small",
                "type": "embedding",
                "usage": "document embedding",
                "optional": True,
                "fallback": None,
            },
        ],
        "workflows": ["classify-invoice", "extract-fields"],
        "agent_types": ["classifier-agent", "extractor-agent"],
        "prompts": ["classify-prompt", "extract-prompt"],
        "estimated_cost_per_run": 0.05,
        "tags": ["finance", "invoice", "classification"],
        "depends_on": [],
        "vectorstore": {
            "collection_name": "invoices",
            "embedding_model": "text-embedding-3-small",
            "chunk_size": 1024,
            "chunk_overlap": 100,
        },
    }
    f = tmp_path / "skill.yaml"
    f.write_text(yaml.dump(data), encoding="utf-8")
    return f


@pytest.fixture
def minimal_manifest_yaml(tmp_path: Path) -> Path:
    """Create a minimal skill.yaml with only required fields."""
    data = {"name": "minimal-skill"}
    f = tmp_path / "skill.yaml"
    f.write_text(yaml.dump(data), encoding="utf-8")
    return f


class TestSkillManifest:
    def test_create_with_all_fields(self):
        m = SkillManifest(
            name="test-skill",
            display_name="Test Skill",
            version="2.0.0",
            skill_type=SkillType.HYBRID,
            description="A test skill",
            author="tester",
            framework_requires=">=0.1.0,<1.0.0",
            capabilities=["cap1", "cap2"],
            required_models=[RequiredModel(name="gpt-4o", type="llm")],
            workflows=["wf1"],
            agent_types=["agent1"],
            prompts=["prompt1"],
            estimated_cost_per_run=0.10,
            tags=["test"],
            depends_on=["base-skill"],
            vectorstore=VectorStoreConfig(collection_name="test-col"),
        )
        assert m.name == "test-skill"
        assert m.display_name == "Test Skill"
        assert m.version == "2.0.0"
        assert m.skill_type == SkillType.HYBRID
        assert m.author == "tester"
        assert len(m.capabilities) == 2
        assert len(m.required_models) == 1
        assert m.required_models[0].name == "gpt-4o"
        assert m.vectorstore is not None
        assert m.vectorstore.collection_name == "test-col"

    def test_create_with_minimal_fields(self):
        m = SkillManifest(name="bare-minimum")
        assert m.name == "bare-minimum"
        assert m.display_name == ""
        assert m.version == "0.1.0"
        assert m.skill_type == SkillType.AI
        assert m.capabilities == []
        assert m.required_models == []
        assert m.vectorstore is None

    def test_defaults_are_correct(self):
        m = SkillManifest(name="defaults-check")
        assert m.description == ""
        assert m.author == ""
        assert m.framework_requires == ">=0.1.0"
        assert m.workflows == []
        assert m.agent_types == []
        assert m.prompts == []
        assert m.estimated_cost_per_run == 0.0
        assert m.tags == []
        assert m.depends_on == []

    def test_skill_type_enum_values(self):
        for st in ["ai", "rpa", "hybrid"]:
            m = SkillManifest(name="enum-test", skill_type=st)
            assert m.skill_type == st

    def test_required_model_with_fallback(self):
        rm = RequiredModel(
            name="gpt-4o",
            type="llm",
            usage="classification",
            optional=False,
            fallback="gpt-4o-mini",
        )
        assert rm.fallback == "gpt-4o-mini"
        assert rm.optional is False

    def test_required_model_defaults(self):
        rm = RequiredModel(name="model-x")
        assert rm.type == "llm"
        assert rm.usage == ""
        assert rm.optional is False
        assert rm.fallback is None

    def test_vectorstore_config_defaults(self):
        vc = VectorStoreConfig()
        assert vc.collection_name == ""
        assert vc.embedding_model == "text-embedding-3-small"
        assert vc.chunk_size == 512
        assert vc.chunk_overlap == 50


class TestLoadManifest:
    def test_load_full_manifest(self, full_manifest_yaml: Path):
        m = load_manifest(full_manifest_yaml)
        assert m.name == "invoice-classifier"
        assert m.display_name == "Invoice Classifier"
        assert m.version == "1.2.0"
        assert len(m.required_models) == 2
        assert m.required_models[0].fallback == "gpt-4o-mini"
        assert m.vectorstore is not None
        assert m.vectorstore.chunk_size == 1024

    def test_load_minimal_manifest(self, minimal_manifest_yaml: Path):
        m = load_manifest(minimal_manifest_yaml)
        assert m.name == "minimal-skill"
        assert m.version == "0.1.0"

    def test_load_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_manifest(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path: Path):
        f = tmp_path / "bad.yaml"
        f.write_text("{{invalid yaml content", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_manifest(f)

    def test_load_non_mapping_yaml_raises(self, tmp_path: Path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            load_manifest(f)


class TestFrameworkCompatibility:
    def test_gte_compatible(self):
        # Current version is 0.1.0
        assert check_framework_compatibility(">=0.1.0") is True

    def test_gte_incompatible(self):
        assert check_framework_compatibility(">=99.0.0") is False

    def test_lte_compatible(self):
        assert check_framework_compatibility("<=1.0.0") is True

    def test_exact_match(self):
        assert check_framework_compatibility("==0.1.0") is True
        assert check_framework_compatibility("==9.9.9") is False

    def test_range_constraint(self):
        assert check_framework_compatibility(">=0.1.0,<1.0.0") is True
        assert check_framework_compatibility(">=0.2.0,<1.0.0") is False

    def test_parse_version(self):
        assert _parse_version("1.2.3") == (1, 2, 3)
        assert _parse_version("0.1.0") == (0, 1, 0)
        assert _parse_version("10") == (10,)
