"""Authentication middleware — enforces auth on all /api/v1/* and /v1/* endpoints."""
from __future__ import annotations

import hashlib
import os

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from aiflow.api.deps import get_engine
from aiflow.security.auth import AuthProvider

__all__ = ["AuthMiddleware"]

logger = structlog.get_logger(__name__)

# Paths that skip authentication entirely
_PUBLIC_PATHS: set[str] = {
    "/api/v1/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Path prefixes that skip authentication
_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/health",
    "/api/v1/health",
)

# Path prefixes that require admin role
_ADMIN_PREFIXES: tuple[str, ...] = (
    "/api/v1/admin",
)

# API key prefix used in DB-based keys
_API_KEY_PREFIX = "aiflow_sk_"


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces Bearer token or API key auth on /api/v1/* and /v1/* routes.

    Public endpoints (login, health, docs) are whitelisted.
    Admin endpoints require admin role.
    Sets request.state.user_id and request.state.role on success.
    """

    def __init__(self, app, auth_provider: AuthProvider | None = None) -> None:
        super().__init__(app)
        if auth_provider:
            self._auth = auth_provider
        else:
            secret = os.getenv("AIFLOW_JWT_SECRET", "dev-secret-change-in-production")
            self._auth = AuthProvider(secret=secret)

    def _is_public(self, path: str) -> bool:
        """Check if the path is publicly accessible without auth."""
        if path in _PUBLIC_PATHS:
            return True
        for prefix in _PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def _requires_admin(self, path: str) -> bool:
        """Check if the path requires admin role."""
        for prefix in _ADMIN_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    async def _verify_api_key(self, key: str) -> tuple[bool, str | None, str]:
        """Verify an API key against the database.

        Returns (is_valid, user_id, role).
        """
        if not key.startswith(_API_KEY_PREFIX):
            return False, None, "viewer"

        prefix = key[:16]
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        engine = await get_engine()
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT ak.user_id, u.role "
                    "FROM api_keys ak "
                    "LEFT JOIN users u ON ak.user_id = u.id "
                    "WHERE ak.prefix = :prefix AND ak.key_hash = :hash AND ak.is_active = true"
                ),
                {"prefix": prefix, "hash": key_hash},
            )
            row = result.fetchone()

        if not row:
            return False, None, "viewer"

        user_id = str(row[0]) if row[0] else None
        role = row[1] or "viewer"

        # Update last_used_at
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE api_keys SET last_used_at = now() WHERE prefix = :prefix"),
                {"prefix": prefix},
            )

        return True, user_id, role

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip auth for non-API paths and public endpoints
        if not (path.startswith("/api/") or path.startswith("/v1/")) or self._is_public(path):
            return await call_next(request)

        # Extract auth from header
        auth_header = request.headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header else ""

        if not token:
            logger.warning("auth_missing", path=path)
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        # Try API key first (starts with aiflow_sk_)
        if token.startswith(_API_KEY_PREFIX):
            is_valid, user_id, role = await self._verify_api_key(token)
            if not is_valid:
                logger.warning("api_key_invalid", path=path)
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
        else:
            # Try JWT token
            result = self._auth.verify_token(token)
            if not result.authenticated:
                logger.warning("token_invalid", path=path, error=result.error)
                return JSONResponse(
                    status_code=401,
                    content={"detail": result.error or "Invalid token"},
                )
            user_id = result.user_id
            role = result.role

        # RBAC: admin endpoints require admin role
        if self._requires_admin(path) and role != "admin":
            logger.warning("admin_access_denied", path=path, user_id=user_id, role=role)
            return JSONResponse(status_code=403, content={"detail": "Admin role required"})

        # Inject auth info into request state
        request.state.user_id = user_id
        request.state.role = role

        return await call_next(request)
