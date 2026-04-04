"""API middleware — auth, rate limiting, security headers, upload size."""

from __future__ import annotations

import hashlib
import os
import time
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from aiflow.api.deps import get_engine
from aiflow.security.auth import AuthProvider

__all__ = [
    "AuthMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "MaxBodySizeMiddleware",
]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Auth Middleware
# ---------------------------------------------------------------------------

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
_ADMIN_PREFIXES: tuple[str, ...] = ("/api/v1/admin",)

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
        self._auth = auth_provider or AuthProvider.from_env()

    def _is_public(self, path: str) -> bool:
        """Check if the path is publicly accessible without auth."""
        if path in _PUBLIC_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)

    def _requires_admin(self, path: str) -> bool:
        """Check if the path requires admin role."""
        return any(path.startswith(prefix) for prefix in _ADMIN_PREFIXES)

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


# ---------------------------------------------------------------------------
# Rate Limit Middleware (Redis sliding window)
# ---------------------------------------------------------------------------

# Default rate limits: (max_requests, window_seconds)
_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "auth": (10, 60),  # 10 req/min for /auth/* (brute force protection)
    "api": (100, 60),  # 100 req/min for /api/* (general)
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter.

    Applies per-IP rate limits:
    - /api/v1/auth/* = 10 req/min (brute force protection)
    - /api/*         = 100 req/min (general)
    Returns 429 Too Many Requests + Retry-After header when exceeded.
    Silently passes through if Redis is unavailable (fail-open).
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._redis = None
        self._initialized = False

    async def _get_redis(self):
        if not self._initialized:
            self._initialized = True
            try:
                import redis.asyncio as aioredis

                url = os.getenv("AIFLOW_REDIS__URL", "redis://localhost:6379/0")
                self._redis = aioredis.from_url(
                    url, decode_responses=False, socket_connect_timeout=2
                )
                await self._redis.ping()
                logger.info("rate_limit_redis_connected", url=url)
            except Exception as exc:
                logger.warning("rate_limit_redis_unavailable", error=str(exc))
                self._redis = None
        return self._redis

    @staticmethod
    def _classify(path: str) -> str | None:
        """Return rate limit bucket name, or None if no limit applies."""
        if path.startswith("/api/v1/auth"):
            return "auth"
        if path.startswith("/api/"):
            return "api"
        return None

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        bucket = self._classify(path)
        if not bucket:
            return await call_next(request)

        max_req, window = _RATE_LIMITS[bucket]
        redis = await self._get_redis()
        if not redis:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"aiflow:rl:{bucket}:{client_ip}"
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex[:8]}"

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.zadd(key, {member: now})
            pipe.expire(key, window + 1)
            results = await pipe.execute()
            current_count = results[1]

            if current_count >= max_req:
                await redis.zrem(key, member)
                logger.warning("rate_limited", ip=client_ip, bucket=bucket, count=current_count)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(window)},
                )
        except Exception as exc:
            logger.warning("rate_limit_check_failed", error=str(exc))

        return await call_next(request)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Content-Security-Policy — restrictive for API responses
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        # HSTS only when served over HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ---------------------------------------------------------------------------
# Max Body Size Middleware (file upload protection)
# ---------------------------------------------------------------------------

# Default: 50 MB
_MAX_BODY_SIZE = int(os.getenv("AIFLOW_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Rejects requests with Content-Length exceeding the configured maximum.

    Protects against oversized file uploads. Default limit: 50 MB.
    Configure via AIFLOW_MAX_UPLOAD_BYTES env var.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_SIZE:
            max_mb = _MAX_BODY_SIZE / (1024 * 1024)
            logger.warning(
                "request_too_large",
                content_length=content_length,
                max_bytes=_MAX_BODY_SIZE,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum: {max_mb:.0f} MB"},
            )
        return await call_next(request)
