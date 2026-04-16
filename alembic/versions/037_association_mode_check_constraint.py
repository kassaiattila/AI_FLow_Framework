"""Enforce: every intake_descriptions row has parent.association_mode set.

Revision ID: 037
Revises: 036
Create Date: 2026-05-16

Phase 1c Day 5 — architect condition C5 part b.

Invariant
---------
    No description may exist under an intake_packages row whose
    association_mode IS NULL.

Why not a plain CHECK on intake_packages
----------------------------------------
A row-level CHECK cannot reference another table (no subquery, no
aggregate). PostgreSQL GENERATED columns also cannot cross-table
aggregate. The closest substitute — materialising a ``has_descriptions``
boolean on intake_packages and keeping it consistent with child row
INSERT/DELETE — is strictly more complex than a trigger and adds a column
whose only consumer is the check itself.

Why trigger on intake_descriptions (not on intake_packages UPDATE)
------------------------------------------------------------------
The semantic invariant is "a description exists => its parent has a
mode". Firing on description INSERT/UPDATE catches every path that can
violate the invariant:

* INSERT:  new description referencing a NULL-mode parent is rejected.
* UPDATE:  re-parenting a description to a NULL-mode package is rejected.

The symmetric concern — a writer flipping an already-populated package's
association_mode back to NULL — is not exercised by any current writer
(grep: the single UPDATE on intake_packages mutates ``status`` only, see
src/aiflow/state/repositories/intake.py transition_status). If a future
writer introduces that path, a mirror trigger can be added; we prefer to
keep today's surface minimal.

Safety / zero-downtime
----------------------
* The trigger function is ``CREATE OR REPLACE`` — idempotent re-run OK.
* The trigger itself is ``CREATE TRIGGER`` (not OR REPLACE — unsupported
  by PG for non-event triggers); a ``DROP TRIGGER IF EXISTS`` precedes
  creation so the migration is also idempotent on re-upgrade paths.
* At 036 head, every package row with description_count > 0 already has
  a non-NULL mode (backfill migration 036), so enabling the trigger
  cannot orphan existing rows.
* Downgrade drops both objects cleanly.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "037"
down_revision: str | None = "036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FN_NAME = "intake_require_association_mode"
_TRIGGER_NAME = "intake_descriptions_require_mode"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_FN_NAME}()
        RETURNS TRIGGER AS $$
        DECLARE
          parent_mode association_mode_enum;
        BEGIN
          SELECT association_mode
            INTO parent_mode
            FROM intake_packages
            WHERE package_id = NEW.package_id;

          IF parent_mode IS NULL THEN
            RAISE EXCEPTION USING
              MESSAGE = format(
                'intake_descriptions requires parent.association_mode '
                '(package_id=%s). Set intake_packages.association_mode '
                'before inserting descriptions.',
                NEW.package_id
              ),
              ERRCODE = 'check_violation';
          END IF;

          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON intake_descriptions")
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER_NAME}
          AFTER INSERT OR UPDATE OF package_id ON intake_descriptions
          FOR EACH ROW
          EXECUTE FUNCTION {_FN_NAME}();
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON intake_descriptions")
    op.execute(f"DROP FUNCTION IF EXISTS {_FN_NAME}()")
