"""Secret management with pluggable providers, TTL caching and resolver chain."""

from __future__ import annotations

import abc
import os
import threading
import time
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import hvac

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
# Environment variable provider (dev / CI / fallback)
# ---------------------------------------------------------------------------


class EnvSecretProvider(SecretProvider):
    """Reads secrets from environment variables.

    Suitable for local development, CI, and as a fallback under Vault.
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
        keys = [k[len(prefix) :].lower() for k in os.environ if k.startswith(prefix)]
        return sorted(keys)


# ---------------------------------------------------------------------------
# HashiCorp Vault KV v2 provider
# ---------------------------------------------------------------------------


class VaultSecretProvider(SecretProvider):
    """HashiCorp Vault KV v2 secret backend.

    Keys use ``path#field`` format:
    ``llm/openai#api_key`` maps to the ``api_key`` field of the secret
    stored at ``<mount_point>/<kv_namespace>/llm/openai``. When ``#field``
    is omitted, the default field name ``value`` is used.

    Authenticates via either a pre-provisioned token or AppRole
    (``role_id`` + ``secret_id``). For tests an already-built ``hvac``
    client may be injected via ``client=``.
    """

    DEFAULT_FIELD = "value"

    def __init__(
        self,
        vault_url: str,
        token: str | None = None,
        *,
        role_id: str | None = None,
        secret_id: str | None = None,
        mount_point: str = "secret",
        kv_namespace: str = "aiflow",
        client: hvac.Client | None = None,
    ) -> None:
        try:
            import hvac as _hvac
        except ImportError as exc:  # pragma: no cover - optional extra
            raise ImportError(
                "VaultSecretProvider requires the 'hvac' package. "
                "Install via `uv sync --extra vault`."
            ) from exc

        self._vault_url = vault_url
        self._role_id = role_id
        self._secret_id = secret_id

        if client is not None:
            self._client = client
        else:
            self._client = _hvac.Client(url=vault_url)
            if token:
                self._client.token = token
            elif role_id and secret_id:
                self._approle_login()
            else:
                raise ValueError(
                    "VaultSecretProvider requires either 'token' or both 'role_id' and 'secret_id'"
                )

        self._mount = mount_point
        self._namespace = kv_namespace.strip("/")
        logger.info(
            "vault_secret_provider_initialized",
            vault_url=vault_url,
            mount=mount_point,
            namespace=self._namespace,
            auth="approle" if role_id else "token",
        )

    # -- Auth --------------------------------------------------------------

    def _approle_login(self) -> None:
        """Exchange AppRole credentials for a fresh client token."""
        if not self._role_id or not self._secret_id:
            raise ValueError("AppRole login requires both role_id and secret_id")
        resp = self._client.auth.approle.login(role_id=self._role_id, secret_id=self._secret_id)
        self._client.token = resp["auth"]["client_token"]
        logger.info(
            "vault_approle_login",
            role_id=self._role_id,
            lease_duration=resp["auth"].get("lease_duration"),
        )

    def renew_token(self, increment: int | None = None) -> dict[str, Any]:
        """Renew the current client token and return the hvac response."""
        resp = self._client.auth.token.renew_self(increment=increment)
        logger.info(
            "vault_token_renewed",
            lease_duration=resp.get("auth", {}).get("lease_duration"),
            increment=increment,
        )
        return resp

    def token_ttl(self) -> int | None:
        """Return the current token TTL (seconds), or ``None`` if unavailable."""
        try:
            info = self._client.auth.token.lookup_self()
        except Exception as exc:  # noqa: BLE001
            logger.warning("vault_token_lookup_failed", error=str(exc))
            return None
        ttl = info.get("data", {}).get("ttl")
        return int(ttl) if ttl is not None else None

    # -- Key helpers -------------------------------------------------------

    def _split_key(self, key: str) -> tuple[str, str]:
        path, sep, field = key.partition("#")
        return path, field if sep else self.DEFAULT_FIELD

    def _full_path(self, path: str) -> str:
        path = path.strip("/")
        return f"{self._namespace}/{path}" if self._namespace else path

    # -- KV v2 CRUD --------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        from hvac.exceptions import InvalidPath

        path, field = self._split_key(key)
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self._mount,
                path=self._full_path(path),
                raise_on_deleted_version=True,
            )
        except InvalidPath:
            logger.debug("vault_secret_get", key=key, found=False)
            return None

        data = resp["data"]["data"]
        value = data.get(field)
        logger.debug("vault_secret_get", key=key, field=field, found=value is not None)
        return value

    def set_secret(self, key: str, value: str) -> None:
        from hvac.exceptions import InvalidPath

        path, field = self._split_key(key)
        full = self._full_path(path)

        existing: dict[str, str] = {}
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self._mount,
                path=full,
                raise_on_deleted_version=True,
            )
            existing = dict(resp["data"]["data"])
        except InvalidPath:
            existing = {}

        existing[field] = value
        self._client.secrets.kv.v2.create_or_update_secret(
            mount_point=self._mount,
            path=full,
            secret=existing,
        )
        logger.info("vault_secret_set", key=key, field=field)

    def delete_secret(self, key: str) -> None:
        path, _field = self._split_key(key)
        full = self._full_path(path)
        try:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                mount_point=self._mount,
                path=full,
            )
            logger.info("vault_secret_deleted", key=key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vault_secret_delete_failed", key=key, error=str(exc))

    def list_keys(self) -> list[str]:
        from hvac.exceptions import InvalidPath

        try:
            resp = self._client.secrets.kv.v2.list_secrets(
                mount_point=self._mount,
                path=self._namespace or "",
            )
        except InvalidPath:
            return []

        raw = resp["data"]["keys"]
        return sorted(raw)


# ---------------------------------------------------------------------------
# SecretManager — resolver chain (cache → primary → fallback → None)
# ---------------------------------------------------------------------------


class _CacheEntry:
    """Internal cache record. ``value=None`` represents a negative lookup."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: str | None, ttl_seconds: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl_seconds


class SecretManager:
    """Wraps :class:`SecretProvider` instances with TTL caching + fallback.

    Resolver order on ``get_secret(key)``:

    1. local cache (positive or negative entry within TTL)
    2. ``provider`` (primary)
    3. ``fallback`` (optional secondary provider)
    4. ``None``

    Negative lookups use a separate (typically shorter) TTL so a repeatedly
    missing key does not hit the primary backend on every call.
    """

    def __init__(
        self,
        provider: SecretProvider,
        fallback: SecretProvider | None = None,
        cache_ttl_seconds: float = 300.0,
        *,
        negative_cache_ttl_seconds: float = 60.0,
    ) -> None:
        self._provider = provider
        self._fallback = fallback
        self._ttl = cache_ttl_seconds
        self._negative_ttl = negative_cache_ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        logger.info(
            "secret_manager_initialized",
            provider=type(provider).__name__,
            fallback=type(fallback).__name__ if fallback else None,
            ttl=cache_ttl_seconds,
            negative_ttl=negative_cache_ttl_seconds,
        )

    # -- Internal helpers --------------------------------------------------

    def _cache_store(self, key: str, value: str | None, ttl: float) -> None:
        with self._lock:
            self._cache[key] = _CacheEntry(value, ttl)

    # -- Public API --------------------------------------------------------

    def get_secret(self, key: str, env_alias: str | None = None) -> str | None:
        """Resolve *key* through cache → primary → fallback → None.

        When *env_alias* is given, the fallback provider is queried with the
        alias instead of *key*, letting the fallback namespace (typically bare
        env vars such as ``OPENAI_API_KEY``) differ from the primary
        (``path#field`` Vault keys). In env-only mode (no fallback) the alias
        is retried against the primary so migrated consumers still resolve
        through their legacy env name.
        """
        now = time.monotonic()
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.expires_at > now:
                logger.debug("secret_cache_hit", key=key, negative=entry.value is None)
                return entry.value

        value = self._provider.get_secret(key)
        if value is not None:
            logger.debug("secret_primary_hit", key=key)
            self._cache_store(key, value, self._ttl)
            return value

        if self._fallback is not None:
            fb_key = env_alias if env_alias is not None else key
            value = self._fallback.get_secret(fb_key)
            if value is not None:
                logger.info(
                    "secret_fallback_hit",
                    key=key,
                    fallback_key=fb_key,
                    fallback=type(self._fallback).__name__,
                )
                self._cache_store(key, value, self._ttl)
                return value
        elif env_alias is not None and env_alias != key:
            value = self._provider.get_secret(env_alias)
            if value is not None:
                logger.info("secret_alias_hit", key=key, env_alias=env_alias)
                self._cache_store(key, value, self._ttl)
                return value

        logger.debug("secret_all_miss", key=key, env_alias=env_alias)
        self._cache_store(key, None, self._negative_ttl)
        return None

    def set_secret(self, key: str, value: str) -> None:
        """Store a secret through the primary provider and cache the value."""
        self._provider.set_secret(key, value)
        self._cache_store(key, value, self._ttl)

    def delete_secret(self, key: str) -> None:
        """Delete the secret from the primary provider and evict the cache."""
        self._provider.delete_secret(key)
        with self._lock:
            self._cache.pop(key, None)

    def list_keys(self) -> list[str]:
        """List keys known to the primary provider."""
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
