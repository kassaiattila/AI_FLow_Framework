"""Pipeline definition CRUD repository (async, PostgreSQL)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.state.models import PipelineDefinitionModel

__all__ = ["PipelineRepository"]

logger = structlog.get_logger(__name__)


class PipelineRepository:
    """Async CRUD for pipeline_definitions table."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._sf = session_factory

    async def create(
        self,
        *,
        name: str,
        version: str,
        yaml_source: str,
        definition: dict[str, Any],
        description: str = "",
        trigger_config: dict[str, Any] | None = None,
        input_schema: dict[str, Any] | None = None,
        enabled: bool = True,
        team_id: uuid.UUID | None = None,
        created_by: str | None = None,
    ) -> PipelineDefinitionModel:
        """Create and persist a new pipeline definition."""
        model = PipelineDefinitionModel(
            name=name,
            version=version,
            description=description,
            yaml_source=yaml_source,
            definition=definition,
            trigger_config=trigger_config or {},
            input_schema=input_schema or {},
            enabled=enabled,
            team_id=team_id,
            created_by=created_by,
        )
        async with self._sf() as session:
            session.add(model)
            await session.commit()
            await session.refresh(model)
        logger.info(
            "pipeline_created",
            id=str(model.id),
            name=name,
            version=version,
        )
        return model

    async def get_by_id(
        self, pipeline_id: uuid.UUID
    ) -> PipelineDefinitionModel | None:
        """Get pipeline by ID."""
        async with self._sf() as session:
            return await session.get(PipelineDefinitionModel, pipeline_id)

    async def get_by_name_version(
        self, name: str, version: str
    ) -> PipelineDefinitionModel | None:
        """Get pipeline by unique (name, version)."""
        async with self._sf() as session:
            stmt = select(PipelineDefinitionModel).where(
                PipelineDefinitionModel.name == name,
                PipelineDefinitionModel.version == version,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        team_id: uuid.UUID | None = None,
        enabled_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PipelineDefinitionModel]:
        """List pipelines with optional filters."""
        async with self._sf() as session:
            stmt = select(PipelineDefinitionModel).order_by(
                PipelineDefinitionModel.updated_at.desc()
            )
            if team_id is not None:
                stmt = stmt.where(
                    PipelineDefinitionModel.team_id == team_id
                )
            if enabled_only:
                stmt = stmt.where(
                    PipelineDefinitionModel.enabled.is_(True)
                )
            stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        pipeline_id: uuid.UUID,
        **kwargs: Any,
    ) -> PipelineDefinitionModel | None:
        """Update pipeline fields. Returns updated model or None."""
        kwargs["updated_at"] = datetime.now(UTC)
        async with self._sf() as session:
            stmt = (
                update(PipelineDefinitionModel)
                .where(PipelineDefinitionModel.id == pipeline_id)
                .values(**kwargs)
                .returning(PipelineDefinitionModel)
            )
            result = await session.execute(stmt)
            await session.commit()
            row = result.scalar_one_or_none()
            if row:
                logger.info("pipeline_updated", id=str(pipeline_id))
            return row

    async def delete(self, pipeline_id: uuid.UUID) -> bool:
        """Delete pipeline. Returns True if deleted."""
        async with self._sf() as session:
            model = await session.get(PipelineDefinitionModel, pipeline_id)
            if model is None:
                return False
            await session.delete(model)
            await session.commit()
            logger.info("pipeline_deleted", id=str(pipeline_id))
            return True

    async def count(
        self,
        *,
        team_id: uuid.UUID | None = None,
        enabled_only: bool = False,
    ) -> int:
        """Count pipelines with optional filters."""
        from sqlalchemy import func

        async with self._sf() as session:
            stmt = select(func.count(PipelineDefinitionModel.id))
            if team_id is not None:
                stmt = stmt.where(
                    PipelineDefinitionModel.team_id == team_id
                )
            if enabled_only:
                stmt = stmt.where(
                    PipelineDefinitionModel.enabled.is_(True)
                )
            result = await session.execute(stmt)
            return result.scalar_one()
