"""PolicyEngine — profile loading, tenant override, capability checks.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N5,
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import asyncpg
import structlog
import yaml

from aiflow.core.errors import CostCapBreached
from aiflow.policy import PolicyConfig
from aiflow.policy.repository import PolicyOverrideRepository
from aiflow.providers.embedder import (
    AzureOpenAIEmbedder,
    BGEM3Embedder,
    EmbedderProvider,
    OpenAIEmbedder,
)
from aiflow.state.cost_repository import CostAttributionRepository

__all__ = [
    "EmbeddingProfile",
    "PolicyEngine",
]

EmbeddingProfile = Literal["A", "B"]

_PROFILE_DEFAULTS: dict[str, type[EmbedderProvider]] = {
    "A": BGEM3Embedder,
    "B": AzureOpenAIEmbedder,
}

_PROVIDER_ALIASES: dict[str, type[EmbedderProvider]] = {
    BGEM3Embedder.PROVIDER_NAME: BGEM3Embedder,
    AzureOpenAIEmbedder.PROVIDER_NAME: AzureOpenAIEmbedder,
    OpenAIEmbedder.PROVIDER_NAME: OpenAIEmbedder,
}

logger = structlog.get_logger(__name__)


class PolicyEngine:
    """Evaluates policy parameters with profile + tenant override merge."""

    def __init__(
        self,
        profile_config: PolicyConfig | None = None,
        tenant_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.profile_config = profile_config if profile_config is not None else PolicyConfig()
        self.tenant_overrides: dict[str, dict[str, Any]] = tenant_overrides or {}
        logger.info(
            "policy_engine_initialized",
            field_count=len(PolicyConfig.model_fields),
            tenant_override_count=len(self.tenant_overrides),
        )

    @classmethod
    def from_yaml(cls, profile_path: Path) -> PolicyEngine:
        """Load a PolicyEngine from a profile YAML file."""
        with open(profile_path) as f:
            data = yaml.safe_load(f)
        policy_data = data.get("policy", {})
        config = PolicyConfig(**policy_data)
        logger.info("policy_engine_loaded_from_yaml", path=str(profile_path))
        return cls(profile_config=config)

    @classmethod
    async def from_yaml_with_db(
        cls,
        profile_path: Path,
        pool: asyncpg.Pool,
    ) -> PolicyEngine:
        """Load profile from YAML + all tenant overrides from DB."""
        with open(profile_path) as f:
            data = yaml.safe_load(f)
        policy_data = data.get("policy", {})
        config = PolicyConfig(**policy_data)

        repo = PolicyOverrideRepository(pool)
        overrides = await repo.get_all_tenant_overrides()

        logger.info(
            "policy_engine_loaded_from_yaml_with_db",
            path=str(profile_path),
            tenant_override_count=len(overrides),
        )
        return cls(profile_config=config, tenant_overrides=overrides)

    def get_for_tenant(self, tenant_id: str) -> PolicyConfig:
        """Return merged config: profile defaults + tenant-specific overrides."""
        override = self.tenant_overrides.get(tenant_id, {})
        if not override:
            return self.profile_config
        merged = self.profile_config.model_dump()
        merged.update(override)
        result = PolicyConfig(**merged)
        logger.debug(
            "policy_tenant_merge",
            tenant_id=tenant_id,
            override_keys=list(override.keys()),
        )
        return result

    def get_for_instance(
        self,
        tenant_id: str,
        instance_override: dict[str, Any] | None = None,
    ) -> PolicyConfig:
        """Return merged config: profile defaults + tenant override + instance override."""
        tenant_config = self.get_for_tenant(tenant_id)
        if not instance_override:
            return tenant_config
        merged = tenant_config.model_dump()
        merged.update(instance_override)
        result = PolicyConfig(**merged)
        logger.debug(
            "policy_instance_merge",
            tenant_id=tenant_id,
            instance_override_keys=list(instance_override.keys()),
        )
        return result

    def is_allowed(self, capability: str, tenant_id: str | None = None) -> bool:
        """Check if a boolean capability is allowed under current policy."""
        cfg = self.get_for_tenant(tenant_id) if tenant_id else self.profile_config
        value = getattr(cfg, capability, False)
        if not isinstance(value, bool):
            return False
        return value

    def get_default_provider(self, provider_type: str, tenant_id: str | None = None) -> str:
        """Return the default provider for a given type (parser, classifier, extractor, embedding)."""
        cfg = self.get_for_tenant(tenant_id) if tenant_id else self.profile_config
        attr_name = f"default_{provider_type}_provider"
        return getattr(cfg, attr_name, "")

    def evaluate(self, parameter: str, tenant_id: str | None = None) -> Any:
        """Get any parameter value with override chain applied."""
        cfg = self.get_for_tenant(tenant_id) if tenant_id else self.profile_config
        return getattr(cfg, parameter, None)

    async def enforce_cost_cap(
        self,
        tenant_id: str,
        pool: asyncpg.Pool,
    ) -> float:
        """Raise ``CostCapBreached`` if the tenant running cost hits its cap.

        Returns the running cost (USD) over the policy-configured window so
        callers can log utilisation even on the pass-through path. No-op when
        ``cost_cap_usd`` is None (the default).
        """
        cfg = self.get_for_tenant(tenant_id)
        cap = cfg.cost_cap_usd
        window_h = cfg.cost_cap_window_h
        if cap is None:
            return 0.0
        repo = CostAttributionRepository(pool)
        current = await repo.aggregate_running_cost(tenant_id, window_h)
        if current >= cap:
            logger.warning(
                "policy_engine.cost_cap_breached",
                tenant_id=tenant_id,
                cap_usd=cap,
                current_usd=current,
                window_h=window_h,
            )
            raise CostCapBreached(
                tenant_id=tenant_id,
                cap_usd=cap,
                current_usd=current,
                window_h=window_h,
            )
        logger.debug(
            "policy_engine.cost_cap_ok",
            tenant_id=tenant_id,
            cap_usd=cap,
            current_usd=current,
            window_h=window_h,
        )
        return current

    def pick_embedder(
        self,
        tenant_id: str,
        profile: EmbeddingProfile,
    ) -> type[EmbedderProvider]:
        """Select the embedder class for a tenant under a given profile.

        Rule:
        * Profile A → BGEM3Embedder (local, free)
        * Profile B → AzureOpenAIEmbedder (cloud, moderate)
        * Tenant override: if ``tenant_overrides[tenant_id]['embedder_provider']``
          is set to a known provider name (``bge_m3`` / ``azure_openai``) that
          class is returned instead.
        """
        if profile not in _PROFILE_DEFAULTS:
            raise ValueError(f"Unknown embedding profile {profile!r}; expected 'A' or 'B'.")
        default_cls = _PROFILE_DEFAULTS[profile]

        override_cls: type[EmbedderProvider] | None = None
        override_name = self.tenant_overrides.get(tenant_id, {}).get("embedder_provider")
        if isinstance(override_name, str):
            if override_name not in _PROVIDER_ALIASES:
                raise ValueError(
                    f"Tenant {tenant_id!r} override embedder_provider={override_name!r} "
                    f"is not a registered embedder. Known: {list(_PROVIDER_ALIASES)}."
                )
            override_cls = _PROVIDER_ALIASES[override_name]

        selected = override_cls or default_cls
        logger.info(
            "policy_engine.embedder_selected",
            tenant_id=tenant_id,
            profile=profile,
            provider=selected.PROVIDER_NAME,
            tenant_override=override_cls is not None,
        )
        return selected
