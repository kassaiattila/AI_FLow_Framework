"""Authentication endpoints — login and token verification."""
from __future__ import annotations

import os

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aiflow.security.auth import AuthProvider

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
async def me(authorization: str = "") -> MeResponse:
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
