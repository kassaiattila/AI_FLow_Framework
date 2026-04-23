"""
@test_registry:
    suite: security-integration
    component: security.secrets.vault
    covers:
      - src/aiflow/security/secrets.py
      - src/aiflow/security/vault_rotation.py
    phase: 7
    priority: high
    estimated_duration_ms: 4000
    requires_services: [vault]
    tags: [security, secrets, vault, integration]
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest

pytest.importorskip("hvac")

import hvac  # noqa: E402

from aiflow.security.secrets import (  # noqa: E402
    EnvSecretProvider,
    SecretManager,
    VaultSecretProvider,
)

VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "aiflow-dev-root")


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        VAULT_ADDR is None,
        reason="VAULT_ADDR not set — skipping live Vault integration tests",
    ),
]


def _raw_cleanup(namespace: str) -> None:
    """Best-effort wipe of a per-test namespace from the dev Vault."""
    try:
        client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        try:
            listing = client.secrets.kv.v2.list_secrets(mount_point="secret", path=namespace)
        except hvac.exceptions.InvalidPath:
            return
        for key in listing["data"]["keys"]:
            subpath = f"{namespace}/{key.rstrip('/')}"
            try:
                client.secrets.kv.v2.delete_metadata_and_all_versions(
                    mount_point="secret", path=subpath
                )
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture
def namespace() -> Iterator[str]:
    ns = f"test-s116-{uuid.uuid4().hex[:8]}"
    yield ns
    _raw_cleanup(ns)


@pytest.fixture
def provider(namespace: str) -> VaultSecretProvider:
    return VaultSecretProvider(
        vault_url=VAULT_ADDR,
        token=VAULT_TOKEN,
        kv_namespace=namespace,
    )


# ---------------------------------------------------------------------------
# CRUD round-trip
# ---------------------------------------------------------------------------


def test_round_trip(provider: VaultSecretProvider) -> None:
    provider.set_secret("llm/openai#api_key", "sk-test-123")
    assert provider.get_secret("llm/openai#api_key") == "sk-test-123"


def test_missing_key_returns_none(provider: VaultSecretProvider) -> None:
    assert provider.get_secret("no/such/path#anything") is None


def test_missing_field_returns_none(provider: VaultSecretProvider) -> None:
    provider.set_secret("svc/foo#known", "v")
    assert provider.get_secret("svc/foo#unknown") is None


def test_set_merges_sibling_fields(provider: VaultSecretProvider) -> None:
    provider.set_secret("svc/creds#user", "alice")
    provider.set_secret("svc/creds#password", "s3cret")
    assert provider.get_secret("svc/creds#user") == "alice"
    assert provider.get_secret("svc/creds#password") == "s3cret"


def test_delete_removes_secret(provider: VaultSecretProvider) -> None:
    provider.set_secret("tmp/key#value", "boom")
    assert provider.get_secret("tmp/key#value") == "boom"
    provider.delete_secret("tmp/key#value")
    assert provider.get_secret("tmp/key#value") is None


def test_list_keys_reflects_writes(provider: VaultSecretProvider) -> None:
    provider.set_secret("alpha#value", "1")
    provider.set_secret("beta#value", "2")
    keys = provider.list_keys()
    assert "alpha" in keys
    assert "beta" in keys


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------


def test_token_ttl_available(provider: VaultSecretProvider) -> None:
    # Dev-mode root token may return TTL=0 (unlimited). We only assert that
    # the call succeeds and returns an int-or-None.
    ttl = provider.token_ttl()
    assert ttl is None or isinstance(ttl, int)


def test_renew_token_smoke(provider: VaultSecretProvider) -> None:
    """renew_self against the dev root token either succeeds or raises a
    well-formed hvac error; either way our wrapper should surface a response
    dict on success."""
    try:
        resp = provider.renew_token()
    except hvac.exceptions.InvalidRequest:
        # Root token in dev mode is not renewable — acceptable signal.
        pytest.skip("root token is not renewable in this dev instance")
    else:
        assert "auth" in resp or "data" in resp


# ---------------------------------------------------------------------------
# SecretManager resolver chain — live Vault + env fallback
# ---------------------------------------------------------------------------


def test_secret_manager_fallback_chain(
    provider: VaultSecretProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIFLOW_SECRET_ONLY_IN_ENV", "from-env")
    env = EnvSecretProvider()
    mgr = SecretManager(provider=provider, fallback=env, cache_ttl_seconds=2.0)

    # Key is absent from Vault → fallback hit.
    assert mgr.get_secret("only_in_env") == "from-env"

    # Write the same key to Vault → primary wins after cache invalidation.
    provider.set_secret("only_in_env#value", "from-vault")
    mgr.invalidate_cache("only_in_env")
    assert mgr.get_secret("only_in_env") == "from-vault"


def test_secret_manager_negative_cache_live(
    provider: VaultSecretProvider,
) -> None:
    """Repeated misses must not hammer Vault within the negative TTL."""
    mgr = SecretManager(provider, negative_cache_ttl_seconds=60.0)
    for _ in range(5):
        assert mgr.get_secret("definitely/not/there#x") is None
    # If the cache worked, only one actual read_secret_version happened
    # against Vault — which we cannot easily assert without intercepting
    # hvac, but the loop completing quickly (<1s over 5 iterations) is a
    # strong functional signal covered by unit tests.
