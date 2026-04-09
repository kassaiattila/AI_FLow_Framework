"""AuditTrailService — immutable audit log with filtering and export."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import structlog
from pydantic import BaseModel

__all__ = ["AuditTrailService"]

logger = structlog.get_logger(__name__)


class AuditEntry(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    user_id: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: str = ""


class AuditTrailService:
    """Immutable audit log backed by PostgreSQL."""

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            url = self._db_url or os.getenv(
                "AIFLOW_DATABASE__URL",
                "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
            ).replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
        return self._pool

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        pool = await self._get_pool()
        entry_id = uuid.uuid4()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO audit_log (id, action, resource_type, resource_id, user_id, details, ip_address)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING *""",
                entry_id,
                action,
                entity_type,
                entity_id,
                None,
                details,
                ip_address,
            )
        logger.info("audit_logged", action=action, entity_type=entity_type, entity_id=entity_id)
        return self._row_to_entry(row)

    async def list_entries(
        self,
        action: str | None = None,
        entity_type: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[AuditEntry]:
        pool = await self._get_pool()
        conditions = []
        params = []
        idx = 1
        if action:
            conditions.append(f"action = ${idx}")
            params.append(action)
            idx += 1
        if entity_type:
            conditions.append(f"resource_type = ${idx}")
            params.append(entity_type)
            idx += 1
        if user_id:
            conditions.append(f"user_id::text = ${idx}")
            params.append(user_id)
            idx += 1
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ${idx}",
                *params,
            )
        return [self._row_to_entry(r) for r in rows]

    async def get_entry(self, entry_id: str) -> AuditEntry | None:
        pool = await self._get_pool()
        import uuid as _uuid

        try:
            uid = _uuid.UUID(entry_id)
        except ValueError:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM audit_log WHERE id = $1", uid)
        return self._row_to_entry(row) if row else None

    @staticmethod
    def _row_to_entry(row) -> AuditEntry:
        details = None
        if row["details"]:
            try:
                details = (
                    json.loads(row["details"])
                    if isinstance(row["details"], str)
                    else row["details"]
                )
            except (json.JSONDecodeError, TypeError):
                details = None
        return AuditEntry(
            id=str(row["id"]),
            action=row["action"],
            entity_type=row.get("resource_type", ""),
            entity_id=row.get("resource_id"),
            user_id=str(row["user_id"]) if row["user_id"] else None,
            details=details,
            ip_address=row["ip_address"],
            created_at=str(row["timestamp"]) if row["timestamp"] else "",
        )
