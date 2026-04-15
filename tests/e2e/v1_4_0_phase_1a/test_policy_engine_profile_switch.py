"""PolicyEngine profile-switch E2E — Profile A vs B + tenant/instance merge.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, policy]

Covers Section 5.1-5.4 of 106_: profile loading, tenant override, instance
override (triple merge), capability checks, default provider resolution.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine


class TestProfileLoading:
    def test_profile_a_cloud_disallowed(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        cfg = engine.profile_config
        assert cfg.cloud_ai_allowed is False
        assert cfg.cloud_storage_allowed is False
        assert cfg.document_content_may_leave_tenant is False
        assert cfg.azure_di_enabled is False
        assert cfg.default_embedding_provider == "bge_m3"
        assert cfg.object_store_provider == "local_fs"

    def test_profile_b_cloud_allowed(self, profile_b_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_b_path)
        cfg = engine.profile_config
        assert cfg.cloud_ai_allowed is True
        assert cfg.cloud_storage_allowed is True
        assert cfg.document_content_may_leave_tenant is True
        assert cfg.azure_di_enabled is True
        assert cfg.default_embedding_provider == "azure_openai_embedding_3_small"
        assert cfg.object_store_provider == "azure_blob"

    def test_profile_values_differ(self, profile_a_path: Path, profile_b_path: Path) -> None:
        a = PolicyEngine.from_yaml(profile_a_path).profile_config
        b = PolicyEngine.from_yaml(profile_b_path).profile_config
        assert a.cloud_ai_allowed != b.cloud_ai_allowed
        assert a.default_embedding_provider != b.default_embedding_provider
        assert a.object_store_provider != b.object_store_provider


class TestTenantOverride:
    def test_no_override_returns_profile_defaults(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        cfg = engine.get_for_tenant("unknown_tenant")
        assert cfg.cloud_ai_allowed is False

    def test_tenant_override_applied(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        engine.tenant_overrides["acme"] = {"manual_review_confidence_threshold": 0.9}

        cfg = engine.get_for_tenant("acme")
        assert cfg.manual_review_confidence_threshold == 0.9
        assert cfg.cloud_ai_allowed is False  # untouched

    def test_tenant_override_does_not_leak_to_other_tenant(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        engine.tenant_overrides["acme"] = {"daily_document_cap": 150}

        acme_cfg = engine.get_for_tenant("acme")
        other_cfg = engine.get_for_tenant("other")
        assert acme_cfg.daily_document_cap == 150
        assert other_cfg.daily_document_cap == 100  # fixture profile A


class TestInstanceOverrideTripleMerge:
    def test_triple_merge_instance_wins(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        engine.tenant_overrides["acme"] = {"manual_review_confidence_threshold": 0.8}

        cfg = engine.get_for_instance(
            "acme",
            instance_override={"manual_review_confidence_threshold": 0.95},
        )
        assert cfg.manual_review_confidence_threshold == 0.95

    def test_triple_merge_tenant_shines_through_when_instance_none(
        self, profile_a_path: Path
    ) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        engine.tenant_overrides["acme"] = {"daily_document_cap": 150}

        cfg = engine.get_for_instance("acme", instance_override=None)
        assert cfg.daily_document_cap == 150

    def test_triple_merge_profile_shines_through_when_no_overrides(
        self, profile_a_path: Path
    ) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        cfg = engine.get_for_instance("fresh_tenant", instance_override={})
        assert cfg.daily_document_cap == 100  # profile A fixture default


class TestCapabilityChecks:
    def test_is_allowed_for_boolean_capability(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        assert engine.is_allowed("embedding_enabled") is True
        assert engine.is_allowed("cloud_ai_allowed") is False

    def test_is_allowed_non_boolean_returns_false(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        assert engine.is_allowed("default_parser_provider") is False

    def test_get_default_provider_resolves(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        assert engine.get_default_provider("parser") == "docling_standard"
        assert engine.get_default_provider("classifier") == "hybrid_ml_llm"
        assert engine.get_default_provider("extractor") == "llm_field_extract"
        assert engine.get_default_provider("embedding") == "bge_m3"

    def test_evaluate_returns_typed_value(self, profile_a_path: Path) -> None:
        engine = PolicyEngine.from_yaml(profile_a_path)
        assert engine.evaluate("manual_review_confidence_threshold") == 0.70
        assert engine.evaluate("daily_document_cap") == 100


class TestFieldCount:
    def test_policy_config_field_count_matches_guide(self) -> None:
        # 106_ Section 5.1 specifies ~33 fields; enforce stability.
        assert len(PolicyConfig.model_fields) >= 30


class TestProfileSwitch:
    def test_switching_profile_engine_swaps_whole_config(
        self, profile_a_path: Path, profile_b_path: Path
    ) -> None:
        engine_a = PolicyEngine.from_yaml(profile_a_path)
        engine_b = PolicyEngine.from_yaml(profile_b_path)

        assert engine_a.is_allowed("cloud_ai_allowed") is False
        assert engine_b.is_allowed("cloud_ai_allowed") is True

    @pytest.mark.parametrize(
        ("profile_fixture", "expected_object_store"),
        [
            ("profile_a_path", "local_fs"),
            ("profile_b_path", "azure_blob"),
        ],
    )
    def test_profile_parametrized(
        self,
        profile_fixture: str,
        expected_object_store: str,
        request: pytest.FixtureRequest,
    ) -> None:
        path = request.getfixturevalue(profile_fixture)
        engine = PolicyEngine.from_yaml(path)
        assert engine.profile_config.object_store_provider == expected_object_store
