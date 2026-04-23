"""SecretManager resolver-chain factory (Sprint M / S117).

Wires :class:`AIFlowSettings.vault` into a cached :class:`SecretManager`:

- ``vault.enabled = False`` → env-only provider (bare env vars, no prefix),
  no fallback. ``env_alias`` on :meth:`SecretManager.get_secret` still
  resolves legacy bare env vars.
- ``vault.enabled = True`` → :class:`VaultSecretProvider` as primary (token
  or AppRole auth) with an env fallback for graceful degradation.

Consumers call :func:`get_secret_manager` exactly once per process and then
``mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY")`` —
primary Vault lookup first, legacy env second.
"""

from __future__ import annotations

from functools import lru_cache

import structlog

from aiflow.core.config import AIFlowSettings, get_settings
from aiflow.security.secrets import (
    EnvSecretProvider,
    SecretManager,
    VaultSecretProvider,
)

__all__ = [
    "build_secret_manager",
    "get_secret_manager",
    "reset_secret_manager",
]

logger = structlog.get_logger(__name__)


def build_secret_manager(settings: AIFlowSettings) -> SecretManager:
    """Return a fresh :class:`SecretManager` according to *settings*.vault*."""
    env = EnvSecretProvider(prefix="")

    if not settings.vault.enabled:
        logger.info(
            "secret_manager_built",
            mode="env_only",
            cache_ttl=settings.vault.cache_ttl_seconds,
        )
        return SecretManager(
            provider=env,
            cache_ttl_seconds=settings.vault.cache_ttl_seconds,
            negative_cache_ttl_seconds=settings.vault.negative_cache_ttl_seconds,
        )

    token = settings.vault.token.get_secret_value() if settings.vault.token else None
    secret_id = settings.vault.secret_id.get_secret_value() if settings.vault.secret_id else None
    vault = VaultSecretProvider(
        vault_url=settings.vault.url,
        token=token,
        role_id=settings.vault.role_id,
        secret_id=secret_id,
        mount_point=settings.vault.mount_point,
        kv_namespace=settings.vault.kv_namespace,
    )
    logger.info(
        "secret_manager_built",
        mode="vault+env_fallback",
        vault_url=settings.vault.url,
        auth="approle" if settings.vault.role_id else "token",
        cache_ttl=settings.vault.cache_ttl_seconds,
    )
    return SecretManager(
        provider=vault,
        fallback=env,
        cache_ttl_seconds=settings.vault.cache_ttl_seconds,
        negative_cache_ttl_seconds=settings.vault.negative_cache_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_secret_manager() -> SecretManager:
    """Return the process-wide cached :class:`SecretManager`."""
    return build_secret_manager(get_settings())


def reset_secret_manager() -> None:
    """Clear the cached singleton (used by tests + after settings reloads)."""
    get_secret_manager.cache_clear()
