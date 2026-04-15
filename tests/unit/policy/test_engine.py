"""Unit tests for PolicyConfig + PolicyEngine.

Session: S46 (D0.3) — PolicyEngine + profile configs
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine

PROFILES_DIR = Path(__file__).resolve().parents[3] / "config" / "profiles"


# ---------------------------------------------------------------------------
# PolicyConfig Pydantic model tests
# ---------------------------------------------------------------------------


class TestPolicyConfig:
    def test_defaults_match_profile_a(self) -> None:
        cfg = PolicyConfig()
        assert cfg.cloud_ai_allowed is False
        assert cfg.cloud_storage_allowed is False
        assert cfg.embedding_enabled is True
        assert cfg.self_hosted_parsing_enabled is True
        assert cfg.default_parser_provider == "docling_standard"
        assert cfg.vector_store_provider == "pgvector"
        assert cfg.object_store_provider == "local_fs"

    def test_confidence_threshold_default(self) -> None:
        cfg = PolicyConfig()
        assert cfg.manual_review_confidence_threshold == pytest.approx(0.70)

    def test_confidence_threshold_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            PolicyConfig(manual_review_confidence_threshold=1.5)
        with pytest.raises(ValueError):
            PolicyConfig(manual_review_confidence_threshold=-0.1)

    def test_daily_cap_none_means_unlimited(self) -> None:
        cfg = PolicyConfig()
        assert cfg.daily_document_cap is None
        assert cfg.daily_document_hard_cap is None

    def test_daily_cap_explicit_values(self) -> None:
        cfg = PolicyConfig(daily_document_cap=500, daily_document_hard_cap=1800)
        assert cfg.daily_document_cap == 500
        assert cfg.daily_document_hard_cap == 1800

    def test_hard_cap_less_than_soft_cap_raises(self) -> None:
        with pytest.raises(ValueError, match="daily_document_hard_cap"):
            PolicyConfig(daily_document_cap=500, daily_document_hard_cap=100)

    def test_negative_daily_cap_raises(self) -> None:
        with pytest.raises(ValueError):
            PolicyConfig(daily_document_cap=-1)

    def test_fallback_provider_order_default_empty(self) -> None:
        cfg = PolicyConfig()
        assert cfg.fallback_provider_order == {}

    def test_all_fields_present(self) -> None:
        assert len(PolicyConfig.model_fields) >= 30


# ---------------------------------------------------------------------------
# Profile YAML loading tests
# ---------------------------------------------------------------------------


class TestProfileLoading:
    def test_profile_a_loads(self) -> None:
        engine = PolicyEngine.from_yaml(PROFILES_DIR / "profile_a.yaml")
        cfg = engine.profile_config
        assert cfg.cloud_ai_allowed is False
        assert cfg.azure_di_enabled is False
        assert cfg.default_parser_provider == "docling_standard"
        assert cfg.daily_document_cap == 500
        assert cfg.daily_document_hard_cap == 1800
        assert "parser" in cfg.fallback_provider_order

    def test_profile_b_loads(self) -> None:
        engine = PolicyEngine.from_yaml(PROFILES_DIR / "profile_b.yaml")
        cfg = engine.profile_config
        assert cfg.cloud_ai_allowed is True
        assert cfg.azure_di_enabled is True
        assert cfg.azure_search_enabled is True
        assert cfg.azure_embedding_enabled is True
        assert cfg.default_embedding_provider == "azure_openai_embedding_3_small"
        assert cfg.azure_embedding_model == "text-embedding-3-small"
        assert cfg.object_store_provider == "azure_blob"

    def test_profile_b_inherits_defaults(self) -> None:
        engine = PolicyEngine.from_yaml(PROFILES_DIR / "profile_b.yaml")
        cfg = engine.profile_config
        assert cfg.embedding_enabled is True
        assert cfg.self_hosted_parsing_enabled is True
        assert cfg.default_parser_provider == "docling_standard"
        assert cfg.vector_store_provider == "pgvector"
        assert cfg.archival_pdfa_required is True


# ---------------------------------------------------------------------------
# PolicyEngine tests
# ---------------------------------------------------------------------------


class TestPolicyEngine:
    def test_get_for_tenant_without_override_returns_base(self) -> None:
        cfg = PolicyConfig(cloud_ai_allowed=False)
        engine = PolicyEngine(profile_config=cfg)
        result = engine.get_for_tenant("tenant_x")
        assert result.cloud_ai_allowed is False
        assert result is cfg

    def test_get_for_tenant_with_override_merges(self) -> None:
        cfg = PolicyConfig(cloud_ai_allowed=False)
        engine = PolicyEngine(
            profile_config=cfg,
            tenant_overrides={"tenant_x": {"cloud_ai_allowed": True}},
        )
        result = engine.get_for_tenant("tenant_x")
        assert result.cloud_ai_allowed is True
        assert engine.profile_config.cloud_ai_allowed is False

    def test_is_allowed_true(self) -> None:
        cfg = PolicyConfig(azure_di_enabled=True)
        engine = PolicyEngine(profile_config=cfg)
        assert engine.is_allowed("azure_di_enabled") is True

    def test_is_allowed_false(self) -> None:
        cfg = PolicyConfig(azure_di_enabled=False)
        engine = PolicyEngine(profile_config=cfg)
        assert engine.is_allowed("azure_di_enabled") is False

    def test_is_allowed_nonexistent_capability(self) -> None:
        engine = PolicyEngine(profile_config=PolicyConfig())
        assert engine.is_allowed("nonexistent_capability") is False

    def test_is_allowed_non_bool_returns_false(self) -> None:
        engine = PolicyEngine(profile_config=PolicyConfig())
        assert engine.is_allowed("default_parser_provider") is False

    def test_is_allowed_with_tenant_override(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(cloud_ai_allowed=False),
            tenant_overrides={"t1": {"cloud_ai_allowed": True}},
        )
        assert engine.is_allowed("cloud_ai_allowed") is False
        assert engine.is_allowed("cloud_ai_allowed", tenant_id="t1") is True

    def test_get_default_provider_parser(self) -> None:
        engine = PolicyEngine(profile_config=PolicyConfig())
        assert engine.get_default_provider("parser") == "docling_standard"

    def test_get_default_provider_embedding(self) -> None:
        engine = PolicyEngine(profile_config=PolicyConfig())
        assert engine.get_default_provider("embedding") == "bge_m3"

    def test_get_default_provider_with_tenant_override(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(),
            tenant_overrides={
                "azure_tenant": {
                    "default_embedding_provider": "azure_openai_embedding_3_small",
                }
            },
        )
        assert engine.get_default_provider("embedding") == "bge_m3"
        assert (
            engine.get_default_provider("embedding", tenant_id="azure_tenant")
            == "azure_openai_embedding_3_small"
        )

    def test_get_default_provider_nonexistent_type(self) -> None:
        engine = PolicyEngine(profile_config=PolicyConfig())
        assert engine.get_default_provider("nonexistent") == ""

    def test_evaluate_returns_value(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(daily_document_cap=500),
        )
        assert engine.evaluate("daily_document_cap") == 500
        assert engine.evaluate("cloud_ai_allowed") is False

    def test_evaluate_nonexistent_returns_none(self) -> None:
        engine = PolicyEngine(profile_config=PolicyConfig())
        assert engine.evaluate("no_such_parameter") is None

    def test_evaluate_with_tenant_override(self) -> None:
        engine = PolicyEngine(
            profile_config=PolicyConfig(daily_document_cap=500),
            tenant_overrides={"t1": {"daily_document_cap": 1000}},
        )
        assert engine.evaluate("daily_document_cap", tenant_id="t1") == 1000
