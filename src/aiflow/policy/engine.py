"""PolicyEngine — profile loading, tenant override, capability checks.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N5,
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from aiflow.policy import PolicyConfig

__all__ = [
    "PolicyEngine",
]

logger = structlog.get_logger(__name__)


class PolicyEngine:
    """Evaluates policy parameters with profile + tenant override merge."""

    def __init__(
        self,
        profile_config: PolicyConfig,
        tenant_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.profile_config = profile_config
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
