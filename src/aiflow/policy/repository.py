"""Async repository for policy_overrides table (raw asyncpg SQL).

Tenant-level and instance-level policy override CRUD.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
import structlog

__all__ = ["PolicyOverrideRepository"]

logger = structlog.get_logger(__name__)


class PolicyOverrideRepository:
    """asyncpg-based CRUD for policy_overrides table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_overrides_for_tenant(
        self,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Get tenant-level override (instance_id IS NULL). Returns None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT policy_json FROM policy_overrides
                WHERE tenant_id = $1 AND instance_id IS NULL
                """,
                tenant_id,
            )
        if row is None:
            return None
        return _parse_jsonb(row["policy_json"])

    async def get_overrides_for_instance(
        self,
        tenant_id: str,
        instance_id: str,
    ) -> dict[str, Any] | None:
        """Get instance-level override. Returns None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT policy_json FROM policy_overrides
                WHERE tenant_id = $1 AND instance_id = $2
                """,
                tenant_id,
                instance_id,
            )
        if row is None:
            return None
        return _parse_jsonb(row["policy_json"])

    async def upsert_override(
        self,
        tenant_id: str,
        policy_json: dict[str, Any],
        instance_id: str | None = None,
    ) -> UUID:
        """Insert or update a policy override. Returns the override_id."""
        async with self._pool.acquire() as conn:
            override_id = await conn.fetchval(
                """
                INSERT INTO policy_overrides (tenant_id, instance_id, policy_json)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT ON CONSTRAINT uq_policy_overrides_tenant_instance
                DO UPDATE SET policy_json = EXCLUDED.policy_json, updated_at = NOW()
                RETURNING override_id
                """,
                tenant_id,
                instance_id,
                json.dumps(policy_json),
            )
        logger.info(
            "policy_override_upserted",
            tenant_id=tenant_id,
            instance_id=instance_id,
            override_id=str(override_id),
        )
        return override_id

    async def delete_override(
        self,
        tenant_id: str,
        instance_id: str | None = None,
    ) -> bool:
        """Delete a policy override. Returns True if a row was deleted."""
        async with self._pool.acquire() as conn:
            if instance_id is None:
                result = await conn.execute(
                    """
                    DELETE FROM policy_overrides
                    WHERE tenant_id = $1 AND instance_id IS NULL
                    """,
                    tenant_id,
                )
            else:
                result = await conn.execute(
                    """
                    DELETE FROM policy_overrides
                    WHERE tenant_id = $1 AND instance_id = $2
                    """,
                    tenant_id,
                    instance_id,
                )
        deleted = result.split()[-1] != "0"
        logger.info(
            "policy_override_deleted",
            tenant_id=tenant_id,
            instance_id=instance_id,
            deleted=deleted,
        )
        return deleted

    async def get_all_tenant_overrides(self) -> dict[str, dict[str, Any]]:
        """Load all tenant-level overrides (instance_id IS NULL) as {tenant_id: policy_json}."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tenant_id, policy_json FROM policy_overrides
                WHERE instance_id IS NULL
                """
            )
        return {row["tenant_id"]: _parse_jsonb(row["policy_json"]) for row in rows}


def _parse_jsonb(value: str | dict | None) -> dict[str, Any]:
    """Parse a JSONB value that may come back as str or dict depending on codec."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(value)
