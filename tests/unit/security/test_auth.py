"""
@test_registry:
    suite: security-unit
    component: security.auth
    covers: [src/aiflow/security/auth.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [security, auth, jwt, api-key]
"""
import time
import pytest
from aiflow.security.auth import AuthProvider, APIKeyProvider, TokenPayload, AuthResult


class TestTokenPayload:
    def test_create_payload(self):
        payload = TokenPayload(sub="user-1", team_id="team-1", role="admin")
        assert payload.sub == "user-1"
        assert payload.team_id == "team-1"
        assert payload.role == "admin"

    def test_default_role(self):
        payload = TokenPayload(sub="user-1")
        assert payload.role == "viewer"


class TestAuthProvider:
    @pytest.fixture
    def auth(self):
        return AuthProvider(secret="test-secret-key")

    def test_create_token(self, auth):
        token = auth.create_token(user_id="user-1", team_id="team-1", role="admin")
        assert isinstance(token, str)
        assert "." in token

    def test_verify_valid_token(self, auth):
        token = auth.create_token(user_id="user-1", team_id="team-1", role="developer")
        result = auth.verify_token(token)
        assert result.authenticated is True
        assert result.user_id == "user-1"
        assert result.team_id == "team-1"
        assert result.role == "developer"

    def test_verify_expired_token(self, auth):
        # Create token with 0 TTL (already expired)
        token = auth.create_token(user_id="user-1", ttl=-1)
        result = auth.verify_token(token)
        assert result.authenticated is False
        assert result.error == "token_expired"

    def test_verify_invalid_token(self, auth):
        result = auth.verify_token("garbage.token")
        assert result.authenticated is False

    def test_verify_tampered_token(self, auth):
        token = auth.create_token(user_id="user-1")
        # Tamper with signature
        parts = token.split(".")
        tampered = parts[0] + ".tampered"
        result = auth.verify_token(tampered)
        assert result.authenticated is False

    def test_different_secrets_reject(self):
        auth1 = AuthProvider(secret="secret-1")
        auth2 = AuthProvider(secret="secret-2")
        token = auth1.create_token(user_id="user-1")
        result = auth2.verify_token(token)
        assert result.authenticated is False


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
