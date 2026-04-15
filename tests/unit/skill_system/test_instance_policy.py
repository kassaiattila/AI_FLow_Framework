"""Unit tests for SkillInstance policy_override + PolicyEngine instance merge.

Session: S49 (D0.6) — InstanceConfig.policy_override + PolicyEngine.get_for_instance()
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine
from aiflow.skill_system.instance import InstanceConfig
from aiflow.skill_system.instance_loader import load_instance_config

# ---------------------------------------------------------------------------
# InstanceConfig.policy_override field tests
# ---------------------------------------------------------------------------


class TestInstanceConfigPolicyOverride:
    def test_policy_override_defaults_to_none(self) -> None:
        cfg = InstanceConfig(
            instance_name="test",
            skill_template="aszf_rag",
            customer="acme",
            prompts={"namespace": "acme/aszf_rag"},
        )
        assert cfg.policy_override is None

    def test_policy_override_accepts_dict(self) -> None:
        override = {"cloud_ai_allowed": True, "daily_document_cap": 1000}
        cfg = InstanceConfig(
            instance_name="test",
            skill_template="aszf_rag",
            customer="acme",
            prompts={"namespace": "acme/aszf_rag"},
            policy_override=override,
        )
        assert cfg.policy_override == override

    def test_existing_fields_unchanged_with_policy_override(self) -> None:
        cfg = InstanceConfig(
            instance_name="test_inst",
            skill_template="process_docs",
            customer="bestix",
            version="1.0.0",
            enabled=False,
            prompts={"namespace": "bestix/process_docs"},
            policy_override={"cloud_ai_allowed": True},
        )
        assert cfg.instance_name == "test_inst"
        assert cfg.skill_template == "process_docs"
        assert cfg.customer == "bestix"
        assert cfg.version == "1.0.0"
        assert cfg.enabled is False

    def test_backward_compat_no_policy_override_in_data(self) -> None:
        data = {
            "instance_name": "legacy",
            "skill_template": "aszf_rag",
            "customer": "acme",
            "prompts": {"namespace": "acme/aszf_rag"},
        }
        cfg = InstanceConfig(**data)
        assert cfg.policy_override is None
        assert cfg.instance_name == "legacy"


# ---------------------------------------------------------------------------
# PolicyEngine.get_for_instance() tests
# ---------------------------------------------------------------------------


class TestPolicyEngineGetForInstance:
    def test_without_instance_override_returns_tenant_merge(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(cloud_ai_allowed=False),
            tenant_overrides={"t1": {"daily_document_cap": 200}},
        )
        result = engine.get_for_instance("t1")
        assert result.cloud_ai_allowed is False
        assert result.daily_document_cap == 200

    def test_without_instance_override_no_tenant_override(self) -> None:
        base = PolicyConfig(cloud_ai_allowed=False)
        engine = PolicyEngine(profile_config=base)
        result = engine.get_for_instance("unknown_tenant")
        assert result is base

    def test_instance_override_merges_on_top(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(
                cloud_ai_allowed=False,
                daily_document_cap=None,
            ),
        )
        result = engine.get_for_instance(
            "t1",
            instance_override={"cloud_ai_allowed": True, "daily_document_cap": 500},
        )
        assert result.cloud_ai_allowed is True
        assert result.daily_document_cap == 500

    def test_triple_merge_profile_tenant_instance(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(
                cloud_ai_allowed=False,
                azure_di_enabled=False,
                daily_document_cap=None,
            ),
            tenant_overrides={"t1": {"azure_di_enabled": True}},
        )
        result = engine.get_for_instance(
            "t1",
            instance_override={"cloud_ai_allowed": True, "daily_document_cap": 300},
        )
        assert result.cloud_ai_allowed is True
        assert result.azure_di_enabled is True
        assert result.daily_document_cap == 300

    def test_instance_override_trumps_tenant_override(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(daily_document_cap=None),
            tenant_overrides={"t1": {"daily_document_cap": 500}},
        )
        result = engine.get_for_instance(
            "t1",
            instance_override={"daily_document_cap": 100},
        )
        assert result.daily_document_cap == 100

    def test_instance_override_trumps_profile_default(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(default_parser_provider="docling_standard"),
        )
        result = engine.get_for_instance(
            "t1",
            instance_override={"default_parser_provider": "azure_di"},
        )
        assert result.default_parser_provider == "azure_di"

    def test_base_config_unchanged_after_instance_merge(self) -> None:
        base = PolicyConfig(cloud_ai_allowed=False)
        engine = PolicyEngine(profile_config=base)
        engine.get_for_instance("t1", instance_override={"cloud_ai_allowed": True})
        assert base.cloud_ai_allowed is False

    def test_empty_instance_override_dict_returns_tenant_merge(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(cloud_ai_allowed=False),
            tenant_overrides={"t1": {"daily_document_cap": 200}},
        )
        result = engine.get_for_instance("t1", instance_override={})
        assert result.daily_document_cap == 200
        assert result.cloud_ai_allowed is False


# ---------------------------------------------------------------------------
# Instance loader — policy_override from YAML
# ---------------------------------------------------------------------------


class TestInstanceLoaderPolicyOverride:
    def test_loads_policy_override_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            instance_name: test_with_policy
            skill_template: aszf_rag
            customer: acme
            prompts:
              namespace: acme/aszf_rag
            policy_override:
              cloud_ai_allowed: true
              daily_document_cap: 750
        """)
        p = tmp_path / "instance.yaml"
        p.write_text(yaml_content, encoding="utf-8")

        cfg = load_instance_config(p)
        assert cfg.policy_override == {"cloud_ai_allowed": True, "daily_document_cap": 750}
        assert cfg.instance_name == "test_with_policy"

    def test_yaml_without_policy_override_still_works(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            instance_name: legacy_instance
            skill_template: process_docs
            customer: bestix
            prompts:
              namespace: bestix/process_docs
        """)
        p = tmp_path / "instance.yaml"
        p.write_text(yaml_content, encoding="utf-8")

        cfg = load_instance_config(p)
        assert cfg.policy_override is None
        assert cfg.instance_name == "legacy_instance"

    def test_yaml_with_empty_policy_override(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            instance_name: empty_override
            skill_template: email_intent
            customer: testco
            prompts:
              namespace: testco/email_intent
            policy_override: {}
        """)
        p = tmp_path / "instance_empty.yaml"
        p.write_text(yaml_content, encoding="utf-8")

        cfg = load_instance_config(p)
        assert cfg.policy_override == {}
