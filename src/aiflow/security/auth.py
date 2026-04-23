"""Authentication: JWT tokens (RS256) and API key management."""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from pathlib import Path

import jwt
import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel, Field

__all__ = ["AuthResult", "TokenPayload", "AuthProvider", "APIKeyProvider"]

logger = structlog.get_logger(__name__)

# Default token expiration: 1 hour
DEFAULT_TOKEN_TTL = 3600
ALGORITHM = "RS256"


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
    """JWT-based authentication provider using RS256 asymmetric keys.

    Uses PyJWT with RSA key pair for token signing and verification.
    In dev mode, auto-generates an ephemeral key pair if none is configured.
    In production, requires explicit key paths via environment variables.
    """

    def __init__(self, private_key: bytes | None = None, public_key: bytes | None = None) -> None:
        self._private_key = private_key
        self._public_key = public_key

    @classmethod
    def from_env(cls) -> AuthProvider:
        """Create AuthProvider from environment / Vault configuration.

        Resolver chain per key material:
          1. Vault ``kv/aiflow/jwt#private_pem`` / ``#public_pem`` (value = PEM).
          2. File path from ``AIFLOW_JWT_PRIVATE_KEY_PATH`` (legacy).
          3. Dev/test: ephemeral auto-generated pair (warning logged).
        Production (``AIFLOW_ENVIRONMENT=prod``) still REQUIRES resolved keys.
        """
        from aiflow.security.resolver import get_secret_manager

        env = os.getenv("AIFLOW_ENVIRONMENT", "dev").lower()
        is_production = env in ("production", "prod")

        mgr = get_secret_manager()
        priv_pem = mgr.get_secret("jwt#private_pem")
        pub_pem = mgr.get_secret("jwt#public_pem")

        priv_path = os.getenv("AIFLOW_JWT_PRIVATE_KEY_PATH", "") or os.getenv(
            "AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH", ""
        )
        pub_path = os.getenv("AIFLOW_JWT_PUBLIC_KEY_PATH", "") or os.getenv(
            "AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH", ""
        )

        private_key: bytes | None = None
        public_key: bytes | None = None

        if priv_pem:
            private_key = priv_pem.encode("utf-8")
            logger.info("jwt_private_key_loaded", source="vault")
        elif priv_path and Path(priv_path).is_file():
            private_key = Path(priv_path).read_bytes()
            logger.info("jwt_private_key_loaded", source="path", path=priv_path)

        if pub_pem:
            public_key = pub_pem.encode("utf-8")
            logger.info("jwt_public_key_loaded", source="vault")
        elif pub_path and Path(pub_path).is_file():
            public_key = Path(pub_path).read_bytes()
            logger.info("jwt_public_key_loaded", source="path", path=pub_path)

        if is_production and (not private_key or not public_key):
            raise RuntimeError(
                "JWT RS256 key pair is REQUIRED in production mode. "
                "Generate keys with: scripts/generate_jwt_keys.sh "
                "and set AIFLOW_JWT_PRIVATE_KEY_PATH + AIFLOW_JWT_PUBLIC_KEY_PATH."
            )

        if not private_key or not public_key:
            logger.warning(
                "jwt_auto_generating_ephemeral_keys",
                env=env,
                hint="Run scripts/generate_jwt_keys.sh for persistent keys",
            )
            private_key, public_key = cls._generate_key_pair()

        return cls(private_key=private_key, public_key=public_key)

    @staticmethod
    def _generate_key_pair() -> tuple[bytes, bytes]:
        """Generate an RSA-2048 key pair for JWT signing."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return private_pem, public_pem

    def create_token(
        self,
        user_id: str,
        team_id: str | None = None,
        role: str = "viewer",
        ttl: int = DEFAULT_TOKEN_TTL,
    ) -> str:
        """Create a signed JWT token using RS256."""
        now = time.time()
        payload = {
            "sub": user_id,
            "team_id": team_id,
            "role": role,
            "exp": int(now + ttl),
            "iat": int(now),
        }
        return jwt.encode(payload, self._private_key, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> AuthResult:
        """Verify a JWT token and return auth result."""
        try:
            payload = jwt.decode(token, self._public_key, algorithms=[ALGORITHM])
            return AuthResult(
                authenticated=True,
                user_id=payload["sub"],
                team_id=payload.get("team_id"),
                role=payload.get("role", "viewer"),
            )
        except jwt.ExpiredSignatureError:
            return AuthResult(authenticated=False, error="token_expired")
        except jwt.InvalidTokenError as exc:
            logger.warning("token_verification_failed", error=str(exc))
            return AuthResult(authenticated=False, error="invalid_token")

    def decode_expired_token(self, token: str) -> dict | None:
        """Decode a token without verifying expiration (for refresh grace period)."""
        try:
            return jwt.decode(
                token,
                self._public_key,
                algorithms=[ALGORITHM],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError:
            return None


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
