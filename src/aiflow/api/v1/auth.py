"""Authentication endpoints — login, token verification, token refresh."""
from __future__ import annotations

import os
from datetime import UTC, datetime

import bcrypt
import structlog
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from aiflow.api.deps import get_engine
from aiflow.security.auth import AuthProvider

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

def _init_auth() -> AuthProvider:
    """Initialize AuthProvider with JWT secret validation.

    Production mode requires an explicit AIFLOW_JWT_SECRET (min 32 chars).
    Dev/test mode falls back to a default secret.
    """
    secret = os.getenv("AIFLOW_JWT_SECRET", "")
    env = os.getenv("AIFLOW_ENVIRONMENT", "dev").lower()
    is_production = env in ("production", "prod")

    if is_production:
        if not secret:
            raise RuntimeError(
                "AIFLOW_JWT_SECRET is REQUIRED in production mode. "
                "Set AIFLOW_JWT_SECRET env var (minimum 32 characters)."
            )
        if len(secret) < 32:
            raise RuntimeError(
                f"AIFLOW_JWT_SECRET is too short ({len(secret)} chars). "
                "Minimum 32 characters required for production."
            )
    elif not secret:
        secret = "dev-secret-change-in-production"
        logger.warning("jwt_using_default_secret", env=env)

    return AuthProvider(secret=secret)


_auth = _init_auth()


# --- Models ---


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


# --- Login (DB + bcrypt) ---


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate with username/password, return JWT token.

    Looks up user by email in the database and verifies password with bcrypt.
    """
    from sqlalchemy import text

    engine = await get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, email, name, role, team_id, password_hash "
                "FROM users WHERE email = :email AND is_active = true"
            ),
            {"email": request.username},
        )
        row = result.fetchone()

    if not row:
        logger.warning("login_failed", username=request.username, reason="user_not_found")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, email, name, role, team_id, password_hash = row

    if not password_hash:
        logger.warning("login_failed", username=request.username, reason="no_password_set")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(request.password.encode("utf-8"), password_hash.encode("utf-8")):
        logger.warning("login_failed", username=request.username, reason="wrong_password")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last_login_at
    async with engine.begin() as conn:
        from sqlalchemy import text as t
        await conn.execute(
            t("UPDATE users SET last_login_at = :now WHERE id = :id"),
            {"now": datetime.now(UTC), "id": user_id},
        )

    token = _auth.create_token(
        user_id=str(user_id),
        team_id=str(team_id) if team_id else None,
        role=role,
    )

    logger.info("login_success", user_id=str(user_id), email=email, role=role)
    return LoginResponse(
        token=token,
        user_id=str(user_id),
        role=role,
        team_id=str(team_id) if team_id else None,
    )


# --- Me ---


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
        if result.error == "token_expired":
            import base64
            import json
            import time

            parts = request.token.split(".")
            if len(parts) == 2:
                payload_json = base64.urlsafe_b64decode(parts[0]).decode()
                payload = json.loads(payload_json)
                if time.time() - payload.get("exp", 0) < 300:  # 5-minute grace period
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
