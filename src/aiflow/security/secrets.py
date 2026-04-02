"""Secret management with pluggable providers and TTL caching."""
from __future__ import annotations

import abc
import os
import threading
import time

import structlog

__all__ = [
    "SecretProvider",
    "EnvSecretProvider",
    "VaultSecretProvider",
    "SecretManager",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class SecretProvider(abc.ABC):
    """Abstract interface for secret storage backends."""

    @abc.abstractmethod
    def get_secret(self, key: str) -> str | None:
        """Retrieve a secret value by *key*, or ``None`` if missing."""

    @abc.abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        """Store or update a secret."""

    @abc.abstractmethod
    def delete_secret(self, key: str) -> None:
        """Delete a secret by *key*."""

    @abc.abstractmethod
    def list_keys(self) -> list[str]:
        """Return all known secret key names."""


# ---------------------------------------------------------------------------
# Environment variable provider (dev / CI)
# ---------------------------------------------------------------------------

class EnvSecretProvider(SecretProvider):
    """Reads secrets from environment variables.

    Suitable for local development and CI pipelines.  All keys are stored
    with an optional prefix (default ``AIFLOW_SECRET_``) so they do not
    collide with other env vars.
    """

    def __init__(self, prefix: str = "AIFLOW_SECRET_") -> None:
        self._prefix = prefix
        logger.info("env_secret_provider_initialized", prefix=prefix)

    def _env_key(self, key: str) -> str:
        return f"{self._prefix}{key.upper()}"

    def get_secret(self, key: str) -> str | None:
        value = os.environ.get(self._env_key(key))
        logger.debug("env_secret_get", key=key, found=value is not None)
        return value

    def set_secret(self, key: str, value: str) -> None:
        os.environ[self._env_key(key)] = value
        logger.info("env_secret_set", key=key)

    def delete_secret(self, key: str) -> None:
        env_key = self._env_key(key)
        if env_key in os.environ:
            del os.environ[env_key]
            logger.info("env_secret_deleted", key=key)
        else:
            logger.warning("env_secret_not_found", key=key)

    def list_keys(self) -> list[str]:
        prefix = self._prefix
        keys = [
            k[len(prefix) :].lower()
            for k in os.environ
            if k.startswith(prefix)
        ]
        return sorted(keys)


# ---------------------------------------------------------------------------
# HashiCorp Vault provider (production placeholder)
# ---------------------------------------------------------------------------

class VaultSecretProvider(SecretProvider):
    """Placeholder for HashiCorp Vault integration.

    All methods raise :class:`NotImplementedError` until the ``hvac``
    dependency is wired in.
    """

    def __init__(self, vault_url: str, token: str) -> None:
        self._vault_url = vault_url
        self._token = token
        logger.info("vault_secret_provider_initialized", vault_url=vault_url)

    def get_secret(self, key: str) -> str | None:
        raise NotImplementedError("VaultSecretProvider requires hvac dependency — use EnvSecretProvider as default")

    def set_secret(self, key: str, value: str) -> None:
        raise NotImplementedError("VaultSecretProvider requires hvac dependency — use EnvSecretProvider as default")

    def delete_secret(self, key: str) -> None:
        raise NotImplementedError("VaultSecretProvider requires hvac dependency — use EnvSecretProvider as default")

    def list_keys(self) -> list[str]:
        raise NotImplementedError("VaultSecretProvider requires hvac dependency — use EnvSecretProvider as default")


# ---------------------------------------------------------------------------
# Secret manager with TTL cache
# ---------------------------------------------------------------------------

class _CacheEntry:
    """Internal cache record."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: str, ttl_seconds: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl_seconds


class SecretManager:
    """Wraps a :class:`SecretProvider` and adds a local TTL cache.

    Parameters
    ----------
    provider:
        Backend secret store.
    cache_ttl_seconds:
        How long cached values remain valid (default 300 s / 5 min).
    """

    def __init__(
        self,
        provider: SecretProvider,
        cache_ttl_seconds: float = 300.0,
    ) -> None:
        self._provider = provider
        self._ttl = cache_ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        logger.info(
            "secret_manager_initialized",
            provider=type(provider).__name__,
            ttl=cache_ttl_seconds,
        )

    # -- Public API ---------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        """Get a secret, using cache when available."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.expires_at > time.monotonic():
                logger.debug("secret_cache_hit", key=key)
                return entry.value

        # Cache miss -- fetch from provider
        value = self._provider.get_secret(key)
        if value is not None:
            with self._lock:
                self._cache[key] = _CacheEntry(value, self._ttl)
        logger.debug("secret_cache_miss", key=key, found=value is not None)
        return value

    def set_secret(self, key: str, value: str) -> None:
        """Store a secret and update the cache."""
        self._provider.set_secret(key, value)
        with self._lock:
            self._cache[key] = _CacheEntry(value, self._ttl)

    def delete_secret(self, key: str) -> None:
        """Delete a secret and evict from cache."""
        self._provider.delete_secret(key)
        with self._lock:
            self._cache.pop(key, None)

    def list_keys(self) -> list[str]:
        """List all secret keys from the provider."""
        return self._provider.list_keys()

    def invalidate_cache(self, key: str | None = None) -> None:
        """Invalidate a single key or the entire cache."""
        with self._lock:
            if key is None:
                self._cache.clear()
                logger.info("secret_cache_cleared")
            else:
                self._cache.pop(key, None)
                logger.info("secret_cache_invalidated", key=key)
