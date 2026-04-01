"""Authentication endpoints — login and token verification."""
from __future__ import annotations

import os

import structlog
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from aiflow.security.auth import APIKeyProvider, AuthProvider

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Simple user store — in production use database
_USERS: dict[str, dict[str, str]] = {
    "admin": {"password": "admin", "role": "admin", "team_id": "bestix"},
    "operator": {"password": "operator", "role": "operator", "team_id": "bestix"},
    "viewer": {"password": "viewer", "role": "viewer", "team_id": "bestix"},
}

_auth = AuthProvider(secret=os.getenv("AIFLOW_JWT_SECRET", "dev-secret-change-in-production"))
_api_keys = APIKeyProvider()


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with token."""
    token: str
    user_id: str
    role: str
    team_id: str | None = None
    expires_in: int = 3600


class MeResponse(BaseModel):
    """Current user info."""
    user_id: str
    role: str
    team_id: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate with username/password, return JWT token."""
    user = _USERS.get(request.username)
    if not user or user["password"] != request.password:
        logger.warning("login_failed", username=request.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _auth.create_token(
        user_id=request.username,
        team_id=user.get("team_id"),
        role=user["role"],
    )

    logger.info("login_success", username=request.username, role=user["role"])
    return LoginResponse(
        token=token,
        user_id=request.username,
        role=user["role"],
        team_id=user.get("team_id"),
    )


@router.get("/me", response_model=MeResponse)
async def me(authorization: str = Header("")) -> MeResponse:
    """Get current user info from token.

    Expects Authorization header: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")

    token = authorization.replace("Bearer ", "").strip()
    result = _auth.verify_token(token)

    if not result.authenticated:
        raise HTTPException(status_code=401, detail=result.error or "Invalid token")

    return MeResponse(
        user_id=result.user_id or "",
        role=result.role,
        team_id=result.team_id,
    )


# --- Token refresh ---


class RefreshRequest(BaseModel):
    """Token refresh request."""
    token: str


class RefreshResponse(BaseModel):
    """Token refresh response."""
    token: str
    expires_in: int = 3600


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest) -> RefreshResponse:
    """Refresh a JWT token. Accepts a valid (or recently expired) token."""
    result = _auth.verify_token(request.token)

    if not result.authenticated:
        # Allow refresh of recently expired tokens (within 24h grace period)
        if result.error == "token_expired":
            import base64
            import json

            parts = request.token.split(".")
            if len(parts) == 2:
                payload_json = base64.urlsafe_b64decode(parts[0]).decode()
                payload = json.loads(payload_json)
                import time

                if time.time() - payload.get("exp", 0) < 86400:
                    new_token = _auth.create_token(
                        user_id=payload["sub"],
                        team_id=payload.get("team_id"),
                        role=payload.get("role", "viewer"),
                    )
                    logger.info("token_refreshed", user_id=payload["sub"], expired=True)
                    return RefreshResponse(token=new_token)

        raise HTTPException(status_code=401, detail=result.error or "Invalid token")

    new_token = _auth.create_token(
        user_id=result.user_id or "",
        team_id=result.team_id,
        role=result.role,
    )
    logger.info("token_refreshed", user_id=result.user_id)
    return RefreshResponse(token=new_token)


# --- API key management ---


class APIKeyCreateRequest(BaseModel):
    """API key creation request."""
    name: str = "default"


class APIKeyCreateResponse(BaseModel):
    """API key creation response. key is only shown once!"""
    key: str
    prefix: str
    name: str


class APIKeyListResponse(BaseModel):
    """List of API key prefixes."""
    keys: list[dict[str, str]]


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    authorization: str = Header(""),
) -> APIKeyCreateResponse:
    """Create a new API key. Requires admin authentication."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.replace("Bearer ", "").strip()
    result = _auth.verify_token(token)
    if not result.authenticated or result.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    full_key, prefix, _ = _api_keys.generate_key(result.user_id or "unknown")
    logger.info("api_key_created", user_id=result.user_id, prefix=prefix, name=request.name)
    return APIKeyCreateResponse(key=full_key, prefix=prefix, name=request.name)


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(authorization: str = Header("")) -> APIKeyListResponse:
    """List API key prefixes (not the full keys)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.replace("Bearer ", "").strip()
    result = _auth.verify_token(token)
    if not result.authenticated:
        raise HTTPException(status_code=401, detail="Invalid token")

    keys = [{"prefix": p} for p in _api_keys._keys.keys()]
    return APIKeyListResponse(keys=keys)


@router.delete("/api-keys/{prefix}")
async def revoke_api_key(prefix: str, authorization: str = Header("")) -> dict:
    """Revoke an API key by prefix."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.replace("Bearer ", "").strip()
    result = _auth.verify_token(token)
    if not result.authenticated or result.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    if prefix not in _api_keys._keys:
        raise HTTPException(status_code=404, detail=f"API key with prefix '{prefix}' not found")

    del _api_keys._keys[prefix]
    logger.info("api_key_revoked", prefix=prefix, user_id=result.user_id)
    return {"revoked": True, "prefix": prefix}
