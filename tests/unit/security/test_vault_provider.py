"""
@test_registry:
    suite: security-unit
    component: security.secrets.vault
    covers:
      - src/aiflow/security/secrets.py
      - src/aiflow/security/vault_rotation.py
    phase: 7
    priority: high
    estimated_duration_ms: 300
    requires_services: []
    tags: [security, secrets, vault, unit]
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

pytest.importorskip("hvac")

import hvac  # noqa: E402
from hvac.exceptions import InvalidPath  # noqa: E402

from aiflow.security.secrets import (  # noqa: E402
    EnvSecretProvider,
    SecretManager,
    SecretProvider,
    VaultSecretProvider,
)
from aiflow.security.vault_rotation import (  # noqa: E402
    VaultTokenRotator,
    start_token_rotation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_client(
    *,
    read_data: dict | None = None,
    read_raises: Exception | None = None,
    list_keys: list[str] | None = None,
    list_raises: Exception | None = None,
) -> MagicMock:
    """Build a MagicMock that mimics the subset of hvac.Client we use."""
    client = MagicMock(spec_set=hvac.Client)
    kv = client.secrets.kv.v2

    if read_raises is not None:
        kv.read_secret_version.side_effect = read_raises
    else:
        kv.read_secret_version.return_value = {
            "data": {"data": read_data or {}},
        }

    if list_raises is not None:
        kv.list_secrets.side_effect = list_raises
    else:
        kv.list_secrets.return_value = {
            "data": {"keys": list(list_keys or [])},
        }

    client.auth.token.renew_self.return_value = {
        "auth": {"client_token": "renewed", "lease_duration": 7200}
    }
    client.auth.token.lookup_self.return_value = {"data": {"ttl": 3600, "renewable": True}}
    client.auth.approle.login.return_value = {
        "auth": {"client_token": "approle-tok", "lease_duration": 7200}
    }
    return client


def _make_provider(**overrides) -> VaultSecretProvider:
    client = overrides.pop("client", None) or _make_fake_client()
    return VaultSecretProvider(
        vault_url="http://localhost:8210",
        client=client,
        kv_namespace=overrides.pop("kv_namespace", "aiflow"),
        mount_point=overrides.pop("mount_point", "secret"),
        **overrides,
    )


# ---------------------------------------------------------------------------
# VaultSecretProvider — construction & auth
# ---------------------------------------------------------------------------


class TestVaultSecretProviderConstruction:
    def test_rejects_missing_credentials(self, monkeypatch):
        """Constructor must refuse without token or full AppRole pair."""
        monkeypatch.setattr(hvac, "Client", MagicMock())
        with pytest.raises(ValueError, match="token.*role_id.*secret_id"):
            VaultSecretProvider(vault_url="http://localhost:8210")

    def test_token_auth_sets_client_token(self, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(hvac, "Client", MagicMock(return_value=fake_client))
        VaultSecretProvider(vault_url="http://x", token="root-tok")
        assert fake_client.token == "root-tok"

    def test_approle_login_invoked(self, monkeypatch):
        fake_client = MagicMock()
        fake_client.auth.approle.login.return_value = {
            "auth": {"client_token": "client-from-approle", "lease_duration": 3600}
        }
        monkeypatch.setattr(hvac, "Client", MagicMock(return_value=fake_client))

        VaultSecretProvider(
            vault_url="http://x",
            role_id="role-123",
            secret_id="sec-456",
        )

        fake_client.auth.approle.login.assert_called_once_with(
            role_id="role-123", secret_id="sec-456"
        )
        assert fake_client.token == "client-from-approle"

    def test_injected_client_skips_auth_setup(self):
        """Providing client= must bypass both token + AppRole flows."""
        client = _make_fake_client()
        VaultSecretProvider(
            vault_url="http://x",
            client=client,
        )
        client.auth.approle.login.assert_not_called()


# ---------------------------------------------------------------------------
# VaultSecretProvider — get_secret
# ---------------------------------------------------------------------------


class TestVaultSecretProviderGet:
    def test_path_and_field_split(self):
        client = _make_fake_client(read_data={"api_key": "abc123"})
        provider = _make_provider(client=client)

        value = provider.get_secret("llm/openai#api_key")

        assert value == "abc123"
        client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            mount_point="secret",
            path="aiflow/llm/openai",
            raise_on_deleted_version=True,
        )

    def test_default_field_when_no_hash(self):
        client = _make_fake_client(read_data={"value": "plain"})
        provider = _make_provider(client=client)

        assert provider.get_secret("simple/key") == "plain"

    def test_missing_field_returns_none(self):
        """Path exists but requested field is absent → None."""
        client = _make_fake_client(read_data={"other_field": "x"})
        provider = _make_provider(client=client)

        assert provider.get_secret("some/path#missing") is None

    def test_invalid_path_returns_none(self):
        client = _make_fake_client(read_raises=InvalidPath("no such path"))
        provider = _make_provider(client=client)

        assert provider.get_secret("nope#field") is None

    def test_empty_namespace_path(self):
        client = _make_fake_client(read_data={"value": "v"})
        provider = _make_provider(client=client, kv_namespace="")

        provider.get_secret("direct/path")
        args = client.secrets.kv.v2.read_secret_version.call_args
        assert args.kwargs["path"] == "direct/path"


# ---------------------------------------------------------------------------
# VaultSecretProvider — set_secret / delete / list
# ---------------------------------------------------------------------------


class TestVaultSecretProviderMutations:
    def test_set_merges_existing_fields(self):
        """set_secret must preserve sibling fields at the same path."""
        client = _make_fake_client(read_data={"user": "alice"})
        provider = _make_provider(client=client)

        provider.set_secret("svc/creds#token", "xyz")

        call = client.secrets.kv.v2.create_or_update_secret.call_args
        assert call.kwargs["path"] == "aiflow/svc/creds"
        assert call.kwargs["secret"] == {"user": "alice", "token": "xyz"}

    def test_set_creates_new_when_path_missing(self):
        client = _make_fake_client(read_raises=InvalidPath("no such"))
        provider = _make_provider(client=client)

        provider.set_secret("new/path#value", "hello")

        call = client.secrets.kv.v2.create_or_update_secret.call_args
        assert call.kwargs["secret"] == {"value": "hello"}

    def test_delete_invokes_metadata_delete(self):
        client = _make_fake_client()
        provider = _make_provider(client=client)

        provider.delete_secret("some/path#ignored")

        client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once_with(
            mount_point="secret", path="aiflow/some/path"
        )

    def test_delete_swallows_backend_error(self):
        """Deletion failure should log but not raise."""
        client = _make_fake_client()
        client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = RuntimeError("boom")
        provider = _make_provider(client=client)

        # Should not raise.
        provider.delete_secret("x/y#z")

    def test_list_keys_returns_sorted(self):
        client = _make_fake_client(list_keys=["zeta", "alpha", "middle"])
        provider = _make_provider(client=client)

        assert provider.list_keys() == ["alpha", "middle", "zeta"]

    def test_list_keys_invalid_path_returns_empty(self):
        client = _make_fake_client(list_raises=InvalidPath("empty"))
        provider = _make_provider(client=client)

        assert provider.list_keys() == []


# ---------------------------------------------------------------------------
# VaultSecretProvider — token management
# ---------------------------------------------------------------------------


class TestVaultSecretProviderTokens:
    def test_renew_token_passes_increment(self):
        client = _make_fake_client()
        provider = _make_provider(client=client)

        resp = provider.renew_token(increment=86400)

        client.auth.token.renew_self.assert_called_once_with(increment=86400)
        assert resp["auth"]["client_token"] == "renewed"

    def test_token_ttl_returns_int(self):
        client = _make_fake_client()
        provider = _make_provider(client=client)

        assert provider.token_ttl() == 3600

    def test_token_ttl_returns_none_on_failure(self):
        client = _make_fake_client()
        client.auth.token.lookup_self.side_effect = RuntimeError("vault down")
        provider = _make_provider(client=client)

        assert provider.token_ttl() is None


# ---------------------------------------------------------------------------
# SecretManager — resolver chain + negative cache
# ---------------------------------------------------------------------------


class _StubProvider(SecretProvider):
    """Deterministic SecretProvider used to count lookups."""

    def __init__(self, store: dict[str, str] | None = None) -> None:
        self.store: dict[str, str] = dict(store or {})
        self.get_calls = 0

    def get_secret(self, key: str) -> str | None:
        self.get_calls += 1
        return self.store.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self.store[key] = value

    def delete_secret(self, key: str) -> None:
        self.store.pop(key, None)

    def list_keys(self) -> list[str]:
        return sorted(self.store)


class TestSecretManagerResolver:
    def test_primary_hit(self):
        primary = _StubProvider({"db_pass": "abc"})
        mgr = SecretManager(primary)
        assert mgr.get_secret("db_pass") == "abc"
        assert primary.get_calls == 1

    def test_primary_miss_fallback_hit(self):
        primary = _StubProvider()
        fallback = _StubProvider({"only_here": "yes"})
        mgr = SecretManager(primary, fallback=fallback)
        assert mgr.get_secret("only_here") == "yes"

    def test_primary_wins_over_fallback(self):
        primary = _StubProvider({"shared": "from-primary"})
        fallback = _StubProvider({"shared": "from-fallback"})
        mgr = SecretManager(primary, fallback=fallback)
        assert mgr.get_secret("shared") == "from-primary"

    def test_all_miss_returns_none(self):
        mgr = SecretManager(_StubProvider(), fallback=_StubProvider())
        assert mgr.get_secret("nope") is None

    def test_positive_cache_hit_skips_provider(self):
        primary = _StubProvider({"k": "v"})
        mgr = SecretManager(primary, cache_ttl_seconds=60.0)
        mgr.get_secret("k")
        mgr.get_secret("k")
        mgr.get_secret("k")
        assert primary.get_calls == 1

    def test_negative_cache_blocks_repeated_miss(self):
        primary = _StubProvider()
        fallback = _StubProvider()
        mgr = SecretManager(
            primary,
            fallback=fallback,
            negative_cache_ttl_seconds=60.0,
        )
        mgr.get_secret("missing")
        mgr.get_secret("missing")
        mgr.get_secret("missing")
        assert primary.get_calls == 1
        assert fallback.get_calls == 1

    def test_negative_cache_expiry_rehits_provider(self, monkeypatch):
        """Once the negative TTL passes, primary must be asked again."""
        primary = _StubProvider()
        # Use a clock we can push forward.
        t = [1000.0]
        monkeypatch.setattr("aiflow.security.secrets.time.monotonic", lambda: t[0])
        mgr = SecretManager(primary, negative_cache_ttl_seconds=10.0)

        mgr.get_secret("k")
        t[0] += 20.0  # expire negative cache
        mgr.get_secret("k")
        assert primary.get_calls == 2

    def test_set_secret_caches_value(self):
        primary = _StubProvider()
        mgr = SecretManager(primary)
        mgr.set_secret("new", "fresh")
        # First get hits cache, not provider.
        prev_calls = primary.get_calls
        assert mgr.get_secret("new") == "fresh"
        assert primary.get_calls == prev_calls

    def test_delete_evicts_cache(self):
        primary = _StubProvider({"gone": "x"})
        mgr = SecretManager(primary)
        mgr.get_secret("gone")
        mgr.delete_secret("gone")
        assert mgr.get_secret("gone") is None

    def test_invalidate_single_key(self):
        primary = _StubProvider({"live": "v"})
        mgr = SecretManager(primary)
        mgr.get_secret("live")
        mgr.invalidate_cache("live")
        mgr.get_secret("live")
        assert primary.get_calls == 2

    def test_invalidate_all(self):
        primary = _StubProvider({"a": "1", "b": "2"})
        mgr = SecretManager(primary)
        mgr.get_secret("a")
        mgr.get_secret("b")
        mgr.invalidate_cache()
        mgr.get_secret("a")
        mgr.get_secret("b")
        assert primary.get_calls == 4

    def test_backward_compat_provider_kwarg(self):
        """Existing callers pass provider= positionally/keyword — must still work."""
        env = EnvSecretProvider(prefix="BWCOMPAT_")
        mgr = SecretManager(provider=env, cache_ttl_seconds=10.0)
        assert mgr.get_secret("nope") is None  # no exception


# ---------------------------------------------------------------------------
# VaultTokenRotator
# ---------------------------------------------------------------------------


class _RotatingProvider:
    """Minimal stand-in satisfying VaultSecretProvider's rotation surface."""

    def __init__(self, ttl: int | None = 3600) -> None:
        self.ttl_values = [ttl]
        self.renew_calls: list[int | None] = []

    def token_ttl(self) -> int | None:
        # Pop consistent values; keep last element if list shrinks to 1.
        if len(self.ttl_values) > 1:
            return self.ttl_values.pop(0)
        return self.ttl_values[0]

    def renew_token(self, increment: int | None = None) -> dict:
        self.renew_calls.append(increment)
        return {"auth": {"lease_duration": increment or 0}}


class TestVaultTokenRotator:
    def test_check_once_skips_when_ttl_above_threshold(self):
        provider = _RotatingProvider(ttl=10_000_000)  # way above threshold
        rotator = VaultTokenRotator(
            provider=provider,  # type: ignore[arg-type]
            check_interval=60,
            renew_increment=30 * 24 * 3600,
            renew_at_fraction=0.2,
        )
        assert rotator.check_once() is False
        assert provider.renew_calls == []

    def test_check_once_renews_when_ttl_below_threshold(self):
        provider = _RotatingProvider(ttl=60)  # well below 20% of 30 days
        rotator = VaultTokenRotator(
            provider=provider,  # type: ignore[arg-type]
            check_interval=60,
            renew_increment=30 * 24 * 3600,
            renew_at_fraction=0.2,
        )
        assert rotator.check_once() is True
        assert provider.renew_calls == [30 * 24 * 3600]

    def test_check_once_noop_when_ttl_unavailable(self):
        provider = _RotatingProvider(ttl=None)
        rotator = VaultTokenRotator(provider=provider)  # type: ignore[arg-type]
        assert rotator.check_once() is False
        assert provider.renew_calls == []

    def test_validates_renew_at_fraction(self):
        provider = _RotatingProvider()
        with pytest.raises(ValueError, match="renew_at_fraction"):
            VaultTokenRotator(
                provider=provider,  # type: ignore[arg-type]
                renew_at_fraction=0.0,
            )
        with pytest.raises(ValueError, match="renew_at_fraction"):
            VaultTokenRotator(
                provider=provider,  # type: ignore[arg-type]
                renew_at_fraction=1.0,
            )

    def test_start_stop_lifecycle(self):
        """Daemon thread must start, run at least one cycle, and stop promptly."""
        provider = _RotatingProvider(ttl=60)
        rotator = VaultTokenRotator(
            provider=provider,  # type: ignore[arg-type]
            check_interval=0.05,
            renew_increment=30 * 24 * 3600,
            renew_at_fraction=0.2,
        )
        rotator.start()
        # Give the loop a moment to execute check_once at least once.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not provider.renew_calls:
            time.sleep(0.02)

        assert rotator.is_running
        rotator.stop(timeout=2.0)
        assert not rotator.is_running
        assert provider.renew_calls  # at least one renewal happened

    def test_start_helper_returns_running_rotator(self):
        provider = _RotatingProvider(ttl=10_000_000)
        rotator = start_token_rotation(
            provider,  # type: ignore[arg-type]
            check_interval=0.05,
        )
        try:
            assert rotator.is_running
        finally:
            rotator.stop(timeout=2.0)

    def test_start_is_idempotent(self):
        provider = _RotatingProvider(ttl=10_000_000)
        rotator = VaultTokenRotator(
            provider=provider,  # type: ignore[arg-type]
            check_interval=0.05,
        )
        rotator.start()
        first_thread = rotator._thread
        rotator.start()  # must not spawn a second thread
        assert rotator._thread is first_thread
        rotator.stop(timeout=2.0)

    def test_loop_survives_provider_exception(self):
        """An exception from check_once must not kill the daemon thread."""
        failing_provider = MagicMock()
        failing_provider.token_ttl.side_effect = [
            RuntimeError("transient"),
            10_000_000,  # second cycle succeeds
        ]
        failing_provider.renew_token.return_value = {"auth": {}}
        rotator = VaultTokenRotator(
            provider=failing_provider,  # type: ignore[arg-type]
            check_interval=0.05,
        )
        rotator.start()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and failing_provider.token_ttl.call_count < 2:
            time.sleep(0.02)
        assert rotator.is_running
        rotator.stop(timeout=2.0)
        assert failing_provider.token_ttl.call_count >= 2


# ---------------------------------------------------------------------------
# Sanity: VaultSecretProvider still satisfies SecretProvider ABC
# ---------------------------------------------------------------------------


def test_vault_provider_is_secret_provider():
    provider = _make_provider()
    assert isinstance(provider, SecretProvider)


def test_thread_safety_smoke():
    """Many concurrent get_secret calls must not corrupt the cache."""
    primary = _StubProvider({"shared": "value"})
    mgr = SecretManager(primary)
    results: list[str | None] = []

    def worker() -> None:
        for _ in range(50):
            results.append(mgr.get_secret("shared"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r == "value" for r in results)
    # Cache must have absorbed most calls; at least not 400 provider hits.
    assert primary.get_calls <= 50
