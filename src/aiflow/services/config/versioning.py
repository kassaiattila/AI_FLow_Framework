"""Config versioning service — version, deploy, and rollback service configurations.

Every config change creates a new version. Active config is the one with is_active=True.
Rollback restores a previous version by copying it as a new active version.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "ConfigVersion",
    "ConfigVersioningConfig",
    "ConfigVersioningService",
]

logger = structlog.get_logger(__name__)


class ConfigVersion(BaseModel):
    """A single config version record."""

    id: str
    service_instance_id: str
    version: int
    config: dict[str, Any]
    deployed_at: datetime | None = None
    deployed_by: str | None = None
    is_active: bool = False
    change_description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConfigVersioningConfig(ServiceConfig):
    """Configuration for the config versioning service."""

    pass


class ConfigVersioningService(BaseService):
    """Manages versioned service configurations with deploy/rollback support."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: ConfigVersioningConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        super().__init__(config or ConfigVersioningConfig())

    @property
    def service_name(self) -> str:
        return "config_versioning"

    @property
    def service_description(self) -> str:
        return "Versioned service configuration with deploy and rollback"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        try:
            async with self._session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False

    async def list_versions(
        self, service_instance_id: str
    ) -> list[ConfigVersion]:
        """List all config versions for a service instance, newest first."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, service_instance_id, version, config_jsonb,
                           deployed_at, deployed_by, is_active, change_description, created_at
                    FROM service_config_versions
                    WHERE service_instance_id = :sid
                    ORDER BY version DESC
                """),
                {"sid": service_instance_id},
            )
            rows = result.fetchall()
            return [
                ConfigVersion(
                    id=str(row[0]),
                    service_instance_id=str(row[1]),
                    version=row[2],
                    config=row[3],
                    deployed_at=row[4],
                    deployed_by=row[5],
                    is_active=row[6],
                    change_description=row[7] or "",
                    created_at=row[8],
                )
                for row in rows
            ]

    async def get_active(
        self, service_instance_id: str
    ) -> ConfigVersion | None:
        """Get the currently active config version."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, service_instance_id, version, config_jsonb,
                           deployed_at, deployed_by, is_active, change_description, created_at
                    FROM service_config_versions
                    WHERE service_instance_id = :sid AND is_active = true
                """),
                {"sid": service_instance_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return ConfigVersion(
                id=str(row[0]),
                service_instance_id=str(row[1]),
                version=row[2],
                config=row[3],
                deployed_at=row[4],
                deployed_by=row[5],
                is_active=row[6],
                change_description=row[7] or "",
                created_at=row[8],
            )

    async def deploy(
        self,
        service_instance_id: str,
        config: dict[str, Any],
        deployed_by: str = "system",
        change_description: str = "",
    ) -> ConfigVersion:
        """Deploy a new config version. Deactivates the previous active version."""
        async with self._session_factory() as session:
            # Get next version number
            result = await session.execute(
                text("""
                    SELECT COALESCE(MAX(version), 0) + 1
                    FROM service_config_versions
                    WHERE service_instance_id = :sid
                """),
                {"sid": service_instance_id},
            )
            next_version = result.scalar()

            # Deactivate current active
            await session.execute(
                text("""
                    UPDATE service_config_versions
                    SET is_active = false
                    WHERE service_instance_id = :sid AND is_active = true
                """),
                {"sid": service_instance_id},
            )

            # Insert new version
            new_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            await session.execute(
                text("""
                    INSERT INTO service_config_versions
                        (id, service_instance_id, version, config_jsonb,
                         deployed_at, deployed_by, is_active, change_description, created_at)
                    VALUES (:id, :sid, :version, CAST(:config AS jsonb),
                            :deployed_at, :deployed_by, true, :desc, :created_at)
                """),
                {
                    "id": new_id,
                    "sid": service_instance_id,
                    "version": next_version,
                    "config": json.dumps(config),
                    "deployed_at": now,
                    "deployed_by": deployed_by,
                    "desc": change_description,
                    "created_at": now,
                },
            )
            await session.commit()

            self._logger.info(
                "config_deployed",
                service_instance_id=service_instance_id,
                version=next_version,
                deployed_by=deployed_by,
            )

            return ConfigVersion(
                id=new_id,
                service_instance_id=service_instance_id,
                version=next_version,
                config=config,
                deployed_at=now,
                deployed_by=deployed_by,
                is_active=True,
                change_description=change_description,
                created_at=now,
            )

    async def rollback(
        self,
        service_instance_id: str,
        target_version: int,
        deployed_by: str = "system",
    ) -> ConfigVersion:
        """Rollback to a previous version by creating a new version with the old config."""
        async with self._session_factory() as session:
            # Get the target version's config
            result = await session.execute(
                text("""
                    SELECT config_jsonb
                    FROM service_config_versions
                    WHERE service_instance_id = :sid AND version = :version
                """),
                {"sid": service_instance_id, "version": target_version},
            )
            row = result.fetchone()
            if not row:
                raise ValueError(
                    f"Version {target_version} not found for instance {service_instance_id}"
                )

        # Deploy the old config as a new version
        return await self.deploy(
            service_instance_id=service_instance_id,
            config=row[0],
            deployed_by=deployed_by,
            change_description=f"Rollback to version {target_version}",
        )

    async def diff(
        self,
        service_instance_id: str,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        """Compare two config versions. Returns added/removed/changed keys."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT version, config_jsonb
                    FROM service_config_versions
                    WHERE service_instance_id = :sid AND version IN (:va, :vb)
                    ORDER BY version
                """),
                {"sid": service_instance_id, "va": version_a, "vb": version_b},
            )
            rows = result.fetchall()
            if len(rows) != 2:
                raise ValueError(f"Could not find both versions {version_a} and {version_b}")

            config_a = rows[0][1]
            config_b = rows[1][1]

            added = {k: config_b[k] for k in config_b if k not in config_a}
            removed = {k: config_a[k] for k in config_a if k not in config_b}
            changed = {
                k: {"old": config_a[k], "new": config_b[k]}
                for k in config_a
                if k in config_b and config_a[k] != config_b[k]
            }

            return {
                "version_a": version_a,
                "version_b": version_b,
                "added": added,
                "removed": removed,
                "changed": changed,
            }
