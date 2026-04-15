"""Async repository for IntakePackage persistence (raw asyncpg SQL).

All intake CRUD operations go through this layer.
Atomic insert of package + files + descriptions in a single transaction.
Tenant isolation enforced on every query.
"""

from __future__ import annotations

import json
from uuid import UUID

import asyncpg
import structlog

from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakePackageStatus,
    IntakeSourceType,
)
from aiflow.intake.state_machine import validate_package_transition

__all__ = ["IntakeRepository"]

logger = structlog.get_logger(__name__)


class IntakeRepository:
    """asyncpg-based CRUD repository for IntakePackage domain."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert_package(self, package: IntakePackage) -> None:
        """Insert a new package with all files and descriptions atomically."""
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                    INSERT INTO intake_packages (
                        package_id, source_type, tenant_id, status,
                        source_metadata, package_context, cross_document_signals,
                        created_at, updated_at, received_by,
                        provenance_chain, routing_decision_id, review_task_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                    )
                    """,
                package.package_id,
                package.source_type.value,
                package.tenant_id,
                package.status.value,
                json.dumps(package.source_metadata),
                json.dumps(package.package_context),
                json.dumps(package.cross_document_signals),
                package.created_at,
                package.updated_at,
                package.received_by,
                package.provenance_chain,
                package.routing_decision_id,
                package.review_task_id,
            )

            for f in package.files:
                await conn.execute(
                    """
                        INSERT INTO intake_files (
                            file_id, package_id, file_path, file_name,
                            mime_type, size_bytes, sha256,
                            source_metadata, sequence_index
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                    f.file_id,
                    package.package_id,
                    f.file_path,
                    f.file_name,
                    f.mime_type,
                    f.size_bytes,
                    f.sha256,
                    json.dumps(f.source_metadata),
                    f.sequence_index,
                )

            for d in package.descriptions:
                await conn.execute(
                    """
                        INSERT INTO intake_descriptions (
                            description_id, package_id, text, language,
                            role, association_confidence, association_method
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                    d.description_id,
                    package.package_id,
                    d.text,
                    d.language,
                    d.role.value,
                    d.association_confidence,
                    d.association_method,
                )

            for d in package.descriptions:
                for file_id in d.associated_file_ids:
                    await conn.execute(
                        """
                            INSERT INTO package_associations (file_id, description_id)
                            VALUES ($1, $2)
                            ON CONFLICT DO NOTHING
                            """,
                        file_id,
                        d.description_id,
                    )

        logger.info(
            "intake_package_inserted",
            package_id=str(package.package_id),
            tenant_id=package.tenant_id,
            files=len(package.files),
            descriptions=len(package.descriptions),
        )

    async def get_package(self, package_id: UUID) -> IntakePackage | None:
        """Get a package with all files and descriptions. Returns None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM intake_packages WHERE package_id = $1",
                package_id,
            )
            if row is None:
                return None

            file_rows = await conn.fetch(
                "SELECT * FROM intake_files WHERE package_id = $1 ORDER BY sequence_index NULLS LAST",
                package_id,
            )
            desc_rows = await conn.fetch(
                "SELECT * FROM intake_descriptions WHERE package_id = $1",
                package_id,
            )

            assoc_rows = await conn.fetch(
                """
                SELECT pa.file_id, pa.description_id
                FROM package_associations pa
                JOIN intake_files f ON f.file_id = pa.file_id
                WHERE f.package_id = $1
                """,
                package_id,
            )
            desc_file_map: dict[UUID, list[UUID]] = {}
            for ar in assoc_rows:
                desc_file_map.setdefault(ar["description_id"], []).append(ar["file_id"])

            files = [
                IntakeFile(
                    file_id=fr["file_id"],
                    file_path=fr["file_path"],
                    file_name=fr["file_name"],
                    mime_type=fr["mime_type"],
                    size_bytes=fr["size_bytes"],
                    sha256=fr["sha256"],
                    source_metadata=_parse_jsonb(fr["source_metadata"]),
                    sequence_index=fr["sequence_index"],
                )
                for fr in file_rows
            ]

            descriptions = [
                IntakeDescription(
                    description_id=dr["description_id"],
                    text=dr["text"],
                    language=dr["language"],
                    role=DescriptionRole(dr["role"]),
                    association_confidence=dr["association_confidence"],
                    association_method=dr["association_method"],
                    associated_file_ids=desc_file_map.get(dr["description_id"], []),
                )
                for dr in desc_rows
            ]

            return IntakePackage(
                package_id=row["package_id"],
                source_type=IntakeSourceType(row["source_type"]),
                tenant_id=row["tenant_id"],
                status=IntakePackageStatus(row["status"]),
                source_metadata=_parse_jsonb(row["source_metadata"]),
                package_context=_parse_jsonb(row["package_context"]),
                cross_document_signals=_parse_jsonb(row["cross_document_signals"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                received_by=row["received_by"],
                provenance_chain=row["provenance_chain"] or [],
                routing_decision_id=row["routing_decision_id"],
                review_task_id=row["review_task_id"],
                files=files,
                descriptions=descriptions,
            )

    async def transition_status(
        self,
        package_id: UUID,
        new_status: IntakePackageStatus,
    ) -> None:
        """Atomic status transition with row-level lock and state machine validation.

        Idempotent: if already in target status, returns immediately.

        Raises:
            ValueError: Package not found.
            InvalidStateTransitionError: Transition not allowed by state machine.
        """
        async with self._pool.acquire() as conn, conn.transaction():
            current = await conn.fetchval(
                "SELECT status FROM intake_packages WHERE package_id = $1 FOR UPDATE",
                package_id,
            )
            if current is None:
                raise ValueError(f"Package {package_id} not found")

            current_status = IntakePackageStatus(current)

            if current_status == new_status:
                logger.info(
                    "intake_transition_idempotent_skip",
                    package_id=str(package_id),
                    status=current,
                )
                return

            validate_package_transition(current_status, new_status)

            await conn.execute(
                "UPDATE intake_packages SET status = $1, updated_at = NOW() WHERE package_id = $2",
                new_status.value,
                package_id,
            )

        logger.info(
            "intake_package_status_transitioned",
            package_id=str(package_id),
            from_status=current_status.value,
            to_status=new_status.value,
        )

    async def list_packages(
        self,
        tenant_id: str,
        *,
        status: IntakePackageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IntakePackage]:
        """List packages for a tenant, optionally filtered by status.

        Returns lightweight packages without files/descriptions hydrated.
        Use get_package() for full hydration.
        """
        async with self._pool.acquire() as conn:
            if status is not None:
                rows = await conn.fetch(
                    """
                    SELECT * FROM intake_packages
                    WHERE tenant_id = $1 AND status = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    tenant_id,
                    status.value,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM intake_packages
                    WHERE tenant_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    tenant_id,
                    limit,
                    offset,
                )

        return [_row_to_package(r) for r in rows]


def _parse_jsonb(value: str | dict | None) -> dict:
    """Parse a JSONB value that may come back as str or dict depending on codec."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(value)


def _row_to_package(row: asyncpg.Record) -> IntakePackage:
    """Convert a DB row to IntakePackage (without files/descriptions)."""
    return IntakePackage.model_construct(
        package_id=row["package_id"],
        source_type=IntakeSourceType(row["source_type"]),
        tenant_id=row["tenant_id"],
        status=IntakePackageStatus(row["status"]),
        source_metadata=_parse_jsonb(row["source_metadata"]),
        package_context=_parse_jsonb(row["package_context"]),
        cross_document_signals=_parse_jsonb(row["cross_document_signals"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        received_by=row["received_by"],
        provenance_chain=row["provenance_chain"] or [],
        routing_decision_id=row["routing_decision_id"],
        review_task_id=row["review_task_id"],
        files=[],
        descriptions=[],
    )
