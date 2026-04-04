"""
@test_registry:
    suite: skills-unit
    component: skills.instance_loader
    covers: [src/aiflow/skills/instance_loader.py]
    phase: A
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [skills, instance, loader, yaml, deployment]
"""
from pathlib import Path

import pytest
import yaml

from aiflow.skills.instance import InstanceConfig
from aiflow.skills.instance_loader import (
    DeploymentProfile,
    load_all_instances,
    load_deployment_profile,
    load_instance_config,
)


@pytest.fixture
def instance_yaml(tmp_path: Path) -> Path:
    """Create a minimal instance YAML file."""
    data = {
        "instance_name": "test-rag",
        "display_name": "Test RAG Chat",
        "skill_template": "aszf_rag_chat",
        "version": "0.1.0",
        "customer": "testco",
        "enabled": True,
        "prompts": {
            "namespace": "testco/rag",
            "label": "dev",
        },
        "models": {
            "default": "gpt-4o-mini",
        },
        "budget": {
            "monthly_usd": 50.0,
            "per_run_usd": 0.10,
        },
        "sla": {
            "target_seconds": 5,
            "p95_target_seconds": 10,
        },
        "routing": {
            "input_channel": "api",
            "output_channel": "api",
        },
    }
    p = tmp_path / "test-rag.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


@pytest.fixture
def deployment_dir(tmp_path: Path) -> Path:
    """Create a deployment directory with deployment.yaml + instance files."""
    instances_dir = tmp_path / "instances"
    instances_dir.mkdir()

    # Instance 1
    inst1 = {
        "instance_name": "cust-rag-1",
        "display_name": "Customer RAG 1",
        "skill_template": "aszf_rag_chat",
        "version": "0.1.0",
        "customer": "custx",
        "prompts": {"namespace": "custx/rag1"},
    }
    (instances_dir / "cust-rag-1.yaml").write_text(yaml.dump(inst1), encoding="utf-8")

    # Instance 2
    inst2 = {
        "instance_name": "cust-rag-2",
        "display_name": "Customer RAG 2",
        "skill_template": "aszf_rag_chat",
        "version": "0.1.0",
        "customer": "custx",
        "prompts": {"namespace": "custx/rag2"},
    }
    (instances_dir / "cust-rag-2.yaml").write_text(yaml.dump(inst2), encoding="utf-8")

    # deployment.yaml
    deployment = {
        "customer": {
            "name": "custx",
            "display_name": "Customer X",
            "tier": "business",
        },
        "framework": {"version": "0.1.0"},
        "skill_templates": [{"name": "aszf_rag_chat", "version": "0.1.0"}],
        "instances": [
            {"file": "instances/cust-rag-1.yaml"},
            {"file": "instances/cust-rag-2.yaml"},
        ],
    }
    (tmp_path / "deployment.yaml").write_text(yaml.dump(deployment), encoding="utf-8")

    return tmp_path


class TestLoadInstanceConfig:
    def test_load_valid(self, instance_yaml: Path) -> None:
        config = load_instance_config(instance_yaml)
        assert isinstance(config, InstanceConfig)
        assert config.instance_name == "test-rag"
        assert config.customer == "testco"
        assert config.models.default == "gpt-4o-mini"

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_instance_config(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Expected YAML mapping"):
            load_instance_config(p)

    def test_load_missing_required_fields(self, tmp_path: Path) -> None:
        p = tmp_path / "incomplete.yaml"
        p.write_text(yaml.dump({"instance_name": "x"}), encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid instance config"):
            load_instance_config(p)

    def test_load_with_intents(self, tmp_path: Path) -> None:
        data = {
            "instance_name": "email-test",
            "skill_template": "email_intent_processor",
            "customer": "testco",
            "prompts": {"namespace": "testco/email"},
            "intents": [
                {"name": "claim", "handler": "extract", "priority": 1},
                {"name": "info", "handler": "rag_answer", "auto_respond": True},
            ],
        }
        p = tmp_path / "email.yaml"
        p.write_text(yaml.dump(data), encoding="utf-8")
        config = load_instance_config(p)
        assert len(config.intents) == 2
        assert config.intents[1].auto_respond is True


class TestLoadDeploymentProfile:
    def test_load_valid(self, deployment_dir: Path) -> None:
        profile = load_deployment_profile(deployment_dir / "deployment.yaml")
        assert isinstance(profile, DeploymentProfile)
        assert profile.customer.name == "custx"
        assert profile.customer.tier == "business"
        assert len(profile.skill_templates) == 1
        assert len(profile.instances) == 2

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_deployment_profile(tmp_path / "nonexistent.yaml")


class TestLoadAllInstances:
    def test_load_all(self, deployment_dir: Path) -> None:
        instances = load_all_instances(deployment_dir / "deployment.yaml")
        assert len(instances) == 2
        names = {i.instance_name for i in instances}
        assert names == {"cust-rag-1", "cust-rag-2"}

    def test_customer_mismatch_raises(self, tmp_path: Path) -> None:
        instances_dir = tmp_path / "instances"
        instances_dir.mkdir()

        inst = {
            "instance_name": "wrong-customer",
            "skill_template": "test",
            "customer": "other",
            "prompts": {"namespace": "other/test"},
        }
        (instances_dir / "wrong.yaml").write_text(yaml.dump(inst), encoding="utf-8")

        deployment = {
            "customer": {"name": "expected"},
            "instances": [{"file": "instances/wrong.yaml"}],
        }
        (tmp_path / "deployment.yaml").write_text(yaml.dump(deployment), encoding="utf-8")

        with pytest.raises(ValueError, match="customer"):
            load_all_instances(tmp_path / "deployment.yaml")

    def test_missing_instance_file_raises(self, tmp_path: Path) -> None:
        deployment = {
            "customer": {"name": "testco"},
            "instances": [{"file": "instances/missing.yaml"}],
        }
        (tmp_path / "deployment.yaml").write_text(yaml.dump(deployment), encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            load_all_instances(tmp_path / "deployment.yaml")
