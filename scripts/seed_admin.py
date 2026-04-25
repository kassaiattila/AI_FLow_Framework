#!/usr/bin/env python3
"""Seed the initial admin user in the database.

Usage:
    # With env vars (non-interactive, CI/Docker):
    AIFLOW_ADMIN_EMAIL=admin@example.com AIFLOW_ADMIN_PASSWORD=SecurePass123 python scripts/seed_admin.py

    # Interactive (prompts for email/password):
    python scripts/seed_admin.py
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import bcrypt
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


async def seed_admin() -> None:
    email = os.environ.get("AIFLOW_ADMIN_EMAIL")
    password = os.environ.get("AIFLOW_ADMIN_PASSWORD")

    if not email:
        email = input("Admin email: ").strip()
    if not password:
        password = getpass.getpass("Admin password: ").strip()

    if not email or not password:
        print("ERROR: email and password are required.")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: password must be at least 8 characters.")
        sys.exit(1)

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    db_url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(db_url)

    try:
        async with engine.begin() as conn:
            # Check if user already exists
            result = await conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            )
            existing = result.fetchone()

            if existing:
                # Update password for existing user
                await conn.execute(
                    text(
                        "UPDATE users SET password_hash = :hash, role = 'admin', "
                        "is_active = true, updated_at = :now WHERE email = :email"
                    ),
                    {"hash": password_hash, "email": email, "now": datetime.now(UTC)},
                )
                print(f"Updated existing user: {email} (role=admin, password reset)")
            else:
                # Create new admin user
                user_id = uuid.uuid4()
                now = datetime.now(UTC)
                await conn.execute(
                    text(
                        "INSERT INTO users (id, email, name, role, password_hash, is_active, created_at, updated_at) "
                        "VALUES (:id, :email, :name, 'admin', :hash, true, :now, :now)"
                    ),
                    {
                        "id": user_id,
                        "email": email,
                        "name": email.split("@")[0],
                        "hash": password_hash,
                        "now": now,
                    },
                )
                print(f"Created admin user: {email} (id={user_id})")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_admin())
