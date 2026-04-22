"""Unit tests for PolicyEngine.pick_embedder.

@test_registry
suite: unit
tags: [unit, policy, embedder, sprint_j]

Sprint J / UC2 (v1.4.6 / S100). Covers:
* Profile A default → BGEM3Embedder.
* Profile B default → AzureOpenAIEmbedder.
* Tenant override replaces the profile default.
* Invalid profile + invalid override name raise ValueError.
"""

from __future__ import annotations

import pytest

from aiflow.policy import PolicyConfig
from aiflow.policy.engine import PolicyEngine
from aiflow.providers.embedder import AzureOpenAIEmbedder, BGEM3Embedder


def _make_engine(
    tenant_overrides: dict[str, dict[str, object]] | None = None,
) -> PolicyEngine:
    return PolicyEngine(
        profile_config=PolicyConfig(),
        tenant_overrides=tenant_overrides,
    )


class TestPickEmbedderDefaults:
    def test_profile_a_returns_bge_m3(self) -> None:
        engine = _make_engine()
        assert engine.pick_embedder("tenant-x", "A") is BGEM3Embedder

    def test_profile_b_returns_azure_openai(self) -> None:
        engine = _make_engine()
        assert engine.pick_embedder("tenant-x", "B") is AzureOpenAIEmbedder

    def test_unknown_profile_rejected(self) -> None:
        engine = _make_engine()
        with pytest.raises(ValueError, match="Unknown embedding profile"):
            engine.pick_embedder("tenant-x", "C")  # type: ignore[arg-type]


class TestPickEmbedderTenantOverride:
    def test_tenant_override_switches_from_a_to_azure_openai(self) -> None:
        engine = _make_engine(
            {"tenant-override": {"embedder_provider": "azure_openai"}},
        )
        assert engine.pick_embedder("tenant-override", "A") is AzureOpenAIEmbedder

    def test_tenant_override_switches_from_b_to_bge_m3(self) -> None:
        engine = _make_engine(
            {"tenant-local-only": {"embedder_provider": "bge_m3"}},
        )
        assert engine.pick_embedder("tenant-local-only", "B") is BGEM3Embedder

    def test_tenant_without_override_falls_back_to_profile_default(self) -> None:
        engine = _make_engine(
            {"other-tenant": {"embedder_provider": "azure_openai"}},
        )
        assert engine.pick_embedder("no-override", "A") is BGEM3Embedder

    def test_unknown_override_provider_rejected(self) -> None:
        engine = _make_engine(
            {"tenant-bogus": {"embedder_provider": "does_not_exist"}},
        )
        with pytest.raises(ValueError, match="not a registered embedder"):
            engine.pick_embedder("tenant-bogus", "A")
