"""
@test_registry:
    suite: security-unit
    component: security.auth
    covers: [src/aiflow/security/auth.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [security, auth, jwt, rs256, api-key]
"""

import pytest

from aiflow.security.auth import APIKeyProvider, AuthProvider, TokenPayload


class TestTokenPayload:
    def test_create_payload(self):
        payload = TokenPayload(sub="user-1", team_id="team-1", role="admin")
        assert payload.sub == "user-1"
        assert payload.team_id == "team-1"
        assert payload.role == "admin"

    def test_default_role(self):
        payload = TokenPayload(sub="user-1")
        assert payload.role == "viewer"


class TestAuthProviderRS256:
    """Tests for RS256 JWT authentication."""

    @pytest.fixture
    def auth(self):
        """Create AuthProvider with auto-generated ephemeral keys."""
        priv, pub = AuthProvider._generate_key_pair()
        return AuthProvider(private_key=priv, public_key=pub)

    def test_create_token_returns_jwt(self, auth):
        token = auth.create_token(user_id="user-1", team_id="team-1", role="admin")
        assert isinstance(token, str)
        # Standard JWT has 3 dot-separated parts
        parts = token.split(".")
        assert len(parts) == 3

    def test_verify_valid_token(self, auth):
        token = auth.create_token(user_id="user-1", team_id="team-1", role="developer")
        result = auth.verify_token(token)
        assert result.authenticated is True
        assert result.user_id == "user-1"
        assert result.team_id == "team-1"
        assert result.role == "developer"

    def test_verify_expired_token(self, auth):
        token = auth.create_token(user_id="user-1", ttl=-1)
        result = auth.verify_token(token)
        assert result.authenticated is False
        assert result.error == "token_expired"

    def test_verify_invalid_token(self, auth):
        result = auth.verify_token("not.a.valid.token")
        assert result.authenticated is False
        assert result.error == "invalid_token"

    def test_verify_garbage_string(self, auth):
        result = auth.verify_token("garbage")
        assert result.authenticated is False

    def test_verify_tampered_token(self, auth):
        token = auth.create_token(user_id="user-1")
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".tampered_signature"
        result = auth.verify_token(tampered)
        assert result.authenticated is False

    def test_different_keys_reject(self):
        """Token signed with one key pair must be rejected by a different public key."""
        priv1, pub1 = AuthProvider._generate_key_pair()
        priv2, pub2 = AuthProvider._generate_key_pair()
        auth1 = AuthProvider(private_key=priv1, public_key=pub1)
        auth2 = AuthProvider(private_key=priv2, public_key=pub2)

        token = auth1.create_token(user_id="user-1")
        result = auth2.verify_token(token)
        assert result.authenticated is False

    def test_token_default_role(self, auth):
        token = auth.create_token(user_id="user-1")
        result = auth.verify_token(token)
        assert result.role == "viewer"

    def test_token_none_team_id(self, auth):
        token = auth.create_token(user_id="user-1")
        result = auth.verify_token(token)
        assert result.team_id is None

    def test_token_custom_ttl(self, auth):
        token = auth.create_token(user_id="user-1", ttl=10)
        result = auth.verify_token(token)
        assert result.authenticated is True

    def test_decode_expired_token(self, auth):
        """decode_expired_token should return payload even if expired."""
        token = auth.create_token(user_id="user-1", role="admin", ttl=-1)
        payload = auth.decode_expired_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["role"] == "admin"

    def test_decode_expired_token_invalid(self, auth):
        result = auth.decode_expired_token("not.valid.jwt")
        assert result is None

    def test_generate_key_pair(self):
        """Key pair generation produces valid PEM bytes."""
        priv, pub = AuthProvider._generate_key_pair()
        assert priv.startswith(b"-----BEGIN PRIVATE KEY-----")
        assert pub.startswith(b"-----BEGIN PUBLIC KEY-----")


class TestAuthProviderFromEnv:
    """Tests for AuthProvider.from_env() factory method."""

    def test_from_env_auto_generates_in_dev(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_ENVIRONMENT", "dev")
        monkeypatch.delenv("AIFLOW_JWT_PRIVATE_KEY_PATH", raising=False)
        monkeypatch.delenv("AIFLOW_JWT_PUBLIC_KEY_PATH", raising=False)
        auth = AuthProvider.from_env()
        token = auth.create_token(user_id="test")
        result = auth.verify_token(token)
        assert result.authenticated is True

    def test_from_env_production_requires_keys(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_ENVIRONMENT", "production")
        monkeypatch.delenv("AIFLOW_JWT_PRIVATE_KEY_PATH", raising=False)
        monkeypatch.delenv("AIFLOW_JWT_PUBLIC_KEY_PATH", raising=False)
        monkeypatch.delenv("AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH", raising=False)
        monkeypatch.delenv("AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH", raising=False)
        with pytest.raises(RuntimeError, match="REQUIRED in production"):
            AuthProvider.from_env()

    def test_from_env_loads_key_files(self, monkeypatch, tmp_path):
        priv, pub = AuthProvider._generate_key_pair()
        priv_path = tmp_path / "private.pem"
        pub_path = tmp_path / "public.pem"
        priv_path.write_bytes(priv)
        pub_path.write_bytes(pub)

        monkeypatch.setenv("AIFLOW_ENVIRONMENT", "production")
        monkeypatch.setenv("AIFLOW_JWT_PRIVATE_KEY_PATH", str(priv_path))
        monkeypatch.setenv("AIFLOW_JWT_PUBLIC_KEY_PATH", str(pub_path))

        auth = AuthProvider.from_env()
        token = auth.create_token(user_id="prod-user")
        result = auth.verify_token(token)
        assert result.authenticated is True
        assert result.user_id == "prod-user"


class TestAPIKeyProvider:
    @pytest.fixture
    def provider(self):
        return APIKeyProvider()

    def test_generate_key(self, provider):
        full_key, prefix, key_hash = provider.generate_key(user_id="user-1")
        assert isinstance(full_key, str)
        assert len(prefix) == APIKeyProvider.PREFIX_LENGTH
        assert len(key_hash) == 64  # SHA-256 hex digest
        assert full_key.startswith(prefix)

    def test_verify_valid_key(self, provider):
        full_key, prefix, key_hash = provider.generate_key(user_id="user-1")
        assert provider.verify_key(full_key) is True

    def test_verify_invalid_key(self, provider):
        provider.generate_key(user_id="user-1")
        assert provider.verify_key("completely-wrong-key-value-here") is False
