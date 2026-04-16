"""Backfill intake_packages.association_mode for pre-Phase-1b rows.

Revision ID: 036
Revises: 035
Create Date: 2026-05-15

Phase 1c Day 4 — architect condition C5 part a.

Strategy (per row where association_mode IS NULL):
    description_count == 0            -> leave NULL (valid: no descriptions)
    description_count == 1            -> 'single_description'
    description_count == file_count   -> 'order'   (N/N, file_count > 0)
    otherwise (N/M mismatch)          -> leave NULL + emit WARNING for ops review

Safety:
    - pg_advisory_xact_lock() before the scan so concurrent long-running
      migrations don't race on this id.
    - Chunked: 1000 package_ids per SELECT — avoids a long single statement
      on large tables. The outer Alembic transaction commits all changes
      atomically (standard Alembic behaviour).
    - description_count / file_count come from COUNT() subqueries on
      intake_descriptions / intake_files, keyed by package_id.
    - WARNING log contains package_id + tenant_id + counts only (no PII).

Downgrade:
    No-op. This migration only mutates data; reversing would require
    `UPDATE ... SET association_mode = NULL` which is semantically
    destructive (cannot distinguish pre-backfill NULLs from post-backfill
    NULLs once downstream code has started relying on the filled values).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import structlog
from alembic import op

revision: str = "036"
down_revision: str | None = "035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LOCK_ID = 79104036
_CHUNK = 1000

_logger = structlog.get_logger(__name__)


def _decide_mode(description_count: int, file_count: int) -> str | None:
    """Return the association_mode or None to leave the row NULL.

    Kept in module scope so the integration test can import and exercise
    the decision table directly.
    """
    if description_count == 0:
        return None
    if description_count == 1:
        return "single_description"
    if description_count == file_count and file_count > 0:
        return "order"
    return None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text(f"SELECT pg_advisory_xact_lock({_LOCK_ID})"))

    select_chunk = sa.text(
        """
        SELECT
            p.package_id,
            p.tenant_id,
            COALESCE(d.cnt, 0) AS description_count,
            COALESCE(f.cnt, 0) AS file_count
        FROM intake_packages p
        LEFT JOIN (
            SELECT package_id, COUNT(*) AS cnt
            FROM intake_descriptions
            GROUP BY package_id
        ) d USING (package_id)
        LEFT JOIN (
            SELECT package_id, COUNT(*) AS cnt
            FROM intake_files
            GROUP BY package_id
        ) f USING (package_id)
        WHERE p.association_mode IS NULL
          AND (CAST(:last AS uuid) IS NULL OR p.package_id > CAST(:last AS uuid))
        ORDER BY p.package_id
        LIMIT :limit
        """
    )
    update_one = sa.text(
        "UPDATE intake_packages "
        "SET association_mode = CAST(:mode AS association_mode_enum) "
        "WHERE package_id = :pid"
    )

    last_id: str | None = None
    total_updated = 0
    total_ambiguous = 0

    while True:
        rows = bind.execute(select_chunk, {"last": last_id, "limit": _CHUNK}).fetchall()
        if not rows:
            break

        for pkg_id, tenant_id, dc, fc in rows:
            mode = _decide_mode(int(dc), int(fc))
            if mode is not None:
                bind.execute(update_one, {"mode": mode, "pid": pkg_id})
                total_updated += 1
            elif dc > 0 and fc != dc:
                total_ambiguous += 1
                _logger.warning(
                    "association_mode_backfill_ambiguous",
                    package_id=str(pkg_id),
                    tenant_id=tenant_id,
                    description_count=int(dc),
                    file_count=int(fc),
                )

        last_id = str(rows[-1][0])

    _logger.info(
        "association_mode_backfill_complete",
        rows_updated=total_updated,
        rows_ambiguous=total_ambiguous,
    )


def downgrade() -> None:
    # No-op by design — see module docstring.
    pass
