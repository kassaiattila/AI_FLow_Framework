"""
@test_registry:
    suite: core-unit
    component: security.boot_guards
    covers:
        - src/aiflow/security/boot_guards.py
    phase: v1.7.0
    priority: critical
    estimated_duration_ms: 30
    requires_services: []
    tags: [unit, security, boot_guards, sprint_w, sw_4]
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from aiflow.core.config import AIFlowSettings, VaultSettings
from aiflow.security.boot_guards import (
    BootGuardError,
    enforce_boot_guards,
    vault_root_token_in_prod_violation,
)


def _settings(
    *,
    environment: str = "prod",
    vault_enabled: bool = True,
    token: str | None = "aiflow-dev-root",
    role_id: str | None = None,
    secret_id: str | None = None,
) -> AIFlowSettings:
    s = AIFlowSettings()
    s.environment = environment  # type: ignore[assignment]
    s.vault = VaultSettings(
        enabled=vault_enabled,
        token=SecretStr(token) if token else None,
        role_id=role_id,
        secret_id=SecretStr(secret_id) if secret_id else None,
    )
    return s


class TestVaultRootTokenInProd:
    def test_dev_root_in_prod_violates(self) -> None:
        msg = vault_root_token_in_prod_violation(_settings(token="aiflow-dev-root"))
        assert msg is not None
        assert "aiflow-dev-root" in msg
        assert "AppRole" in msg

    def test_hvs_prefix_in_prod_violates(self) -> None:
        msg = vault_root_token_in_prod_violation(_settings(token="hvs.someRootShape"))
        assert msg is not None
        assert "AppRole" in msg

    def test_approle_token_in_prod_passes(self) -> None:
        # AppRole-issued tokens use hvs.CAES prefix
        msg = vault_root_token_in_prod_violation(_settings(token="hvs.CAESxyz"))
        assert msg is None

    def test_dev_root_with_approle_creds_passes(self) -> None:
        # Operator passed AppRole creds AND a token; trust AppRole
        msg = vault_root_token_in_prod_violation(
            _settings(token="aiflow-dev-root", role_id="r1", secret_id="s1")
        )
        assert msg is None

    def test_dev_environment_no_violation(self) -> None:
        msg = vault_root_token_in_prod_violation(
            _settings(environment="dev", token="aiflow-dev-root")
        )
        assert msg is None

    def test_vault_disabled_no_violation(self) -> None:
        msg = vault_root_token_in_prod_violation(
            _settings(vault_enabled=False, token="aiflow-dev-root")
        )
        assert msg is None

    def test_no_token_no_violation(self) -> None:
        msg = vault_root_token_in_prod_violation(_settings(token=None))
        assert msg is None

    def test_safe_token_no_violation(self) -> None:
        msg = vault_root_token_in_prod_violation(_settings(token="my-non-root-token-shape"))
        assert msg is None

    def test_bypass_env_var_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD", "true")
        msg = vault_root_token_in_prod_violation(_settings(token="aiflow-dev-root"))
        assert msg is None


class TestEnforceBootGuards:
    def test_violation_raises(self) -> None:
        with pytest.raises(BootGuardError) as exc_info:
            enforce_boot_guards(_settings(token="aiflow-dev-root"))
        assert "AppRole" in str(exc_info.value)

    def test_clean_settings_pass(self) -> None:
        # Dev environment with anything → passes
        enforce_boot_guards(_settings(environment="dev"))

    def test_prod_with_approle_passes(self) -> None:
        enforce_boot_guards(_settings(token="hvs.CAESabc", role_id="r1", secret_id="s1"))
