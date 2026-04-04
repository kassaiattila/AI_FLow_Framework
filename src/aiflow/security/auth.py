"""Authentication: JWT tokens and API key management."""
from __future__ import annotations

import hashlib
import secrets
import time

import structlog
from pydantic import BaseModel, Field

__all__ = ["AuthResult", "TokenPayload", "AuthProvider", "APIKeyProvider"]

logger = structlog.get_logger(__name__)

# Default token expiration: 1 hour
DEFAULT_TOKEN_TTL = 3600


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # subject (user_id)
    team_id: str | None = None
    role: str = "viewer"
    exp: float = 0.0  # expiration timestamp
    iat: float = Field(default_factory=time.time)  # issued at


class AuthResult(BaseModel):
    """Result of an authentication attempt."""

    authenticated: bool = False
    user_id: str | None = None
    team_id: str | None = None
    role: str = "viewer"
    error: str | None = None


class AuthProvider:
    """JWT-based authentication provider.

    Uses a shared secret for token signing (HMAC-SHA256).
    In production, use RS256 with public/private key pair.
    """

    def __init__(self, secret: str = "dev-secret-change-in-production") -> None:
        self._secret = secret

    def create_token(
        self,
        user_id: str,
        team_id: str | None = None,
        role: str = "viewer",
        ttl: int = DEFAULT_TOKEN_TTL,
    ) -> str:
        """Create a signed token string.

        Returns a simple base64-style token for testing.
        In production, use PyJWT for proper JWT.
        """
        import base64

        now = time.time()
        payload = TokenPayload(
            sub=user_id,
            team_id=team_id,
            role=role,
            exp=now + ttl,
            iat=now,
        )
        payload_json = payload.model_dump_json()
        # Simple HMAC signature for development
        sig = hashlib.sha256(
            (payload_json + self._secret).encode()
        ).hexdigest()[:16]
        token_data = base64.urlsafe_b64encode(payload_json.encode()).decode()
        return f"{token_data}.{sig}"

    def verify_token(self, token: str) -> AuthResult:
        """Verify a token and return auth result."""
        import base64

        try:
            parts = token.split(".")
            if len(parts) != 2:
                return AuthResult(authenticated=False, error="invalid_token_format")

            payload_b64, sig = parts
            payload_json = base64.urlsafe_b64decode(payload_b64).decode()

            # Verify signature
            expected_sig = hashlib.sha256(
                (payload_json + self._secret).encode()
            ).hexdigest()[:16]
            if sig != expected_sig:
                return AuthResult(authenticated=False, error="invalid_signature")

            payload = TokenPayload.model_validate_json(payload_json)

            # Check expiration
            if payload.exp < time.time():
                return AuthResult(authenticated=False, error="token_expired")

            return AuthResult(
                authenticated=True,
                user_id=payload.sub,
                team_id=payload.team_id,
                role=payload.role,
            )
        except Exception as exc:
            logger.warning("token_verification_failed", error=str(exc))
            return AuthResult(authenticated=False, error=str(exc))


class APIKeyProvider:
    """API key generation and verification."""

    PREFIX_LENGTH = 8

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}  # prefix -> hash

    def generate_key(self, user_id: str) -> tuple[str, str, str]:
        """Generate a new API key.

        Returns (full_key, prefix, key_hash).
        The full key is shown once; only prefix and hash are stored.
        """
        raw_key = secrets.token_urlsafe(32)
        prefix = raw_key[: self.PREFIX_LENGTH]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        self._keys[prefix] = key_hash
        logger.info("api_key_generated", user_id=user_id, prefix=prefix)
        return raw_key, prefix, key_hash

    def verify_key(self, key: str) -> bool:
        """Verify an API key against stored hashes."""
        prefix = key[: self.PREFIX_LENGTH]
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        stored_hash = self._keys.get(prefix)
        return stored_hash == key_hash if stored_hash else False
