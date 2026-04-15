"""SkillInstance policy_override E2E — triple merge with PolicyEngine.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, skill_instance, policy]

Covers 106_ Section 6: InstanceConfig.policy_override field and its
interaction with PolicyEngine.get_for_instance().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.policy.engine import PolicyEngine
from aiflow.skill_system.instance import (
    InstanceConfig,
    PromptConfig,
)


def _instance(
    *,
    policy_override: dict | None = None,
    name: str = "test_instance",
) -> InstanceConfig:
    return InstanceConfig(
        instance_name=name,
        skill_template="document_extractor",
        customer="phase_1a_test_tenant",
        prompts=PromptConfig(namespace="test_ns"),
        policy_override=policy_override,
    )


class TestInstanceConfigSchema:
    def test_policy_override_defaults_to_none(self) -> None:
        inst = _instance()
        assert inst.policy_override is None

    def test_policy_override_accepts_dict(self) -> None:
        override = {"manual_review_confidence_threshold": 0.85}
        inst = _instance(policy_override=override)
        assert inst.policy_override == override

    def test_policy_override_in_model_dump(self) -> None:
        inst = _instance(policy_override={"cloud_ai_allowed": True})
        dumped = inst.model_dump()
        assert dumped["policy_override"] == {"cloud_ai_allowed": True}


class TestTripleMergeWithEngine:
    def test_instance_override_wins_over_tenant(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        engine.tenant_overrides["acme"] = {"manual_review_confidence_threshold": 0.80}

        inst = _instance(policy_override={"manual_review_confidence_threshold": 0.92})
        cfg = engine.get_for_instance("acme", instance_override=inst.policy_override)

        assert cfg.manual_review_confidence_threshold == 0.92

    def test_tenant_shines_through_when_instance_none(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        engine.tenant_overrides["acme"] = {"daily_document_cap": 175}

        inst = _instance(policy_override=None)
        cfg = engine.get_for_instance("acme", instance_override=inst.policy_override)

        assert cfg.daily_document_cap == 175

    def test_profile_shines_through_without_overrides(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        inst = _instance(policy_override=None)
        cfg = engine.get_for_instance("fresh_tenant", instance_override=inst.policy_override)
        assert cfg.manual_review_confidence_threshold == 0.70  # profile A default

    def test_instance_partial_override_only_affects_named_fields(
        self, profile_a_path: Path
    ) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        inst = _instance(policy_override={"daily_document_cap": 50})
        cfg = engine.get_for_instance("fresh_tenant", instance_override=inst.policy_override)

        assert cfg.daily_document_cap == 50
        assert cfg.cloud_ai_allowed is False  # profile default preserved
        assert cfg.default_parser_provider == "docling_standard"


class TestMultipleInstancesIsolated:
    def test_two_instances_same_tenant_diverge(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)

        inst_low = _instance(
            name="low_threshold", policy_override={"manual_review_confidence_threshold": 0.5}
        )
        inst_high = _instance(
            name="high_threshold",
            policy_override={"manual_review_confidence_threshold": 0.95},
        )

        cfg_low = engine.get_for_instance("acme", instance_override=inst_low.policy_override)
        cfg_high = engine.get_for_instance("acme", instance_override=inst_high.policy_override)

        assert cfg_low.manual_review_confidence_threshold == 0.5
        assert cfg_high.manual_review_confidence_threshold == 0.95


class TestValidationThroughPolicyConfig:
    def test_invalid_override_field_value_rejected(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        inst = _instance(policy_override={"manual_review_confidence_threshold": 2.5})

        with pytest.raises(Exception):  # pydantic.ValidationError
            engine.get_for_instance("acme", instance_override=inst.policy_override)
